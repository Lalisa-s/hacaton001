from datetime import UTC, datetime, timedelta
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from app.core.config import Settings
from app.main import create_app
from app.models import User, Account, FamilyMember, Pig
from app.models.family import FamilyInvitation, SharedFamilyAccount, SharedFamilyPig

pytestmark = pytest.mark.anyio
@pytest.fixture
def anyio_backend(): return 'asyncio'
@pytest.fixture
async def app(tmp_path):
    instance=create_app(Settings(_env_file=None,demo_mode=True,database_url=f'sqlite:///{(tmp_path/"family.db").as_posix()}'))
    async with instance.router.lifespan_context(instance): yield instance
@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c: yield c

def actor(id): return {'X-Demo-User-Id':str(id)}

async def test_family_summary_excludes_all_private_resources(client):
    data=(await client.get('/api/v1/family')).json()
    assert data['is_admin'] is True
    assert data['accounts']==data['pigs']==[]
    assert {m['id'] for m in data['members']}=={10,11,20}
    assert all('accounts' not in m and 'balance' not in m for m in data['members'])
    assert (await client.get('/api/v1/family',headers=actor(20))).json()['is_admin'] is False

async def test_only_explicit_resources_are_shared(app,client):
    with app.state.session_factory() as db,db.begin():
        db.add(SharedFamilyAccount(account_id=100,family_id=1))
        db.add(SharedFamilyPig(pig_id=500,family_id=1))
    data=(await client.get('/api/v1/family',headers=actor(20))).json()
    assert [a['id'] for a in data['accounts']]==[100]
    assert [p['id'] for p in data['pigs']]==[500]

async def test_nonadmins_cannot_manage_family(app,client):
    for uid in (11,20):
        assert (await client.post('/api/v1/family/invitations',headers=actor(uid),json={})).status_code==403
        assert (await client.delete('/api/v1/family/members/11',headers=actor(uid))).status_code==403
    assert (await client.delete('/api/v1/family/members/10')).status_code==409
    assert (await client.delete('/api/v1/family/members/999')).status_code==404

async def test_remove_member_preserves_bank_data_and_survives_restart(app,client):
    response=await client.delete('/api/v1/family/members/11')
    assert response.status_code==200,response.text
    assert (await client.get('/api/v1/family',headers=actor(11))).status_code==403
    with app.state.session_factory() as db:
        assert db.get(User,11) is not None
        assert db.get(Account,110).balance==15000
        assert db.get(FamilyMember,11) is None
    from app.db.demo import initialize_demo_database
    initialize_demo_database(app.state.db_engine)
    with app.state.session_factory() as db: assert db.get(FamilyMember,11) is None

async def test_invite_accept_reuse_and_token_privacy(app,client):
    invitation=await client.post('/api/v1/family/invitations',json={})
    assert invitation.status_code==201
    data=invitation.json()
    with app.state.session_factory() as db,db.begin():
        db.add(User(id=30,login='new-relative',role='parent'))
        assert db.get(FamilyInvitation,data['id']).token_hash!=data['token']
    accepted=await client.post('/api/v1/family/invitations/accept',headers=actor(30),json={'token':data['token']})
    assert accepted.status_code==200,accepted.text
    assert (await client.post('/api/v1/family/invitations/accept',headers=actor(30),json={'token':data['token']})).status_code==409
    summary=(await client.get('/api/v1/family',headers=actor(30))).json()
    assert summary['accounts']==summary['pigs']==[]
    assert 'token' not in str(summary)

async def test_expired_invite_and_existing_membership_leave_state_unchanged(app,client):
    data=(await client.post('/api/v1/family/invitations',json={})).json()
    assert (await client.post('/api/v1/family/invitations/accept',json={'token':data['token']})).status_code==409
    with app.state.session_factory() as db,db.begin():
        db.add(User(id=30,login='new-relative',role='parent'))
        db.get(FamilyInvitation,data['id']).expires_at=datetime.now(UTC)-timedelta(seconds=1)
    assert (await client.post('/api/v1/family/invitations/accept',headers=actor(30),json={'token':data['token']})).status_code==409
    with app.state.session_factory() as db: assert db.get(FamilyMember,30) is None

async def test_remove_child_does_not_break_remaining_parent_requests(app,client):
    assert (await client.post('/api/v1/pigs/500/break-requests',headers=actor(20),json={})).status_code==201
    assert (await client.delete('/api/v1/family/members/20')).status_code==200
    requests=await client.get('/api/v1/pig-break-requests')
    assert requests.status_code==200 and requests.json()['items']==[]
    with app.state.session_factory() as db: assert db.get(Pig,500).current_balance==3000
