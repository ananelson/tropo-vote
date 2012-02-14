import web
import re

DB_FILE = '/var/www/tropo-vote/data/vote.sqlite3'
db = web.database(dbn='sqlite', db=DB_FILE)

# Sessions
def new_session(tropo_call_id, caller_network, caller_channel, caller_id):
    db.insert('sessions', **locals())

def session_info(tropo_call_id):
    return db.select('sessions', where='tropo_call_id=$tropo_call_id', vars=locals())[0]

def caller_id_if_valid(tropo_call_id):
    session = session_info(tropo_call_id)
    is_valid_channel = session['caller_network'] in ('SIP', 'SMS')
    is_number = re.match("^(\+)?[0-9]+$", session['caller_id'])
    if is_valid_channel and is_number:
        return session['caller_id']
    else:
        return None

# Votes and Candidates
def caller_id_can_vote(caller_id):
    if caller_id:
        return count_votes_by_caller_id(caller_id) == 0
    else:
        return False

def count_votes_by_caller_id(caller_id):
    results = db.query("SELECT COUNT(*) as count_votes from votes WHERE caller_id=$caller_id", vars=locals())
    return int(results[0].count_votes)

def find_candidate_by_code(vote_code):
    candidates = list(db.select('candidates', where='vote_code=$vote_code', vars=locals()))
    if len(candidates) == 1:
        return candidates[0]
    else:
        return None

def record_vote(caller_id, candidate_id):
    # Create a new vote object
    new_vote(caller_id, candidate_id)
    # increment the cached vote tally
    increment_vote_cache(candidate_id)

def new_vote(caller_id, candidate_id):
    db.insert('votes', **locals())

def increment_vote_cache(candidate_id):
    db.query("UPDATE candidates set cached_votes=cached_votes+1 where id=$candidate_id", vars=locals())

def get_candidates():
    return db.select('candidates', order='vote_code')

