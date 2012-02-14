"""
An app for voting by phone
"""
import sys, os
abspath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(abspath)
sys.path.append("../models")
os.chdir(abspath)

from tropo import Tropo, Choices, Result
import json
import re
import web

import models

urls = (
        '/start', 'StartTropo', # record session info, pass to main menu or SMS handler
        '/vote/(menu|response|confirm)', 'VoteTropo',
        '/vote/(confirm)/(.*)', 'VoteTropo',
        '/', 'Index'
        )

render = web.template.render('../templates/')

class BaseTropo(object):
    """
    Defines some convenience methods.
    """
    def call_id(self):
        data = json.loads(web.data())
        if data.has_key('session'):
            return data['session']['callId']
        elif data.has_key('result'):
            return data['result']['callId']
        else:
            print data
            print data.keys()
            raise Exception("Can't obtain call id, have no session or result")

    def get_result(self):
        return Result(web.data())

    def get_answer(self):
        """
        Retrieves the user-supplied value after an 'ask'
        """
        r = self.get_result()
        try:
            return r.getValue()
        except KeyError:
            return None

class MenuTropo(BaseTropo):
    URL_ROOT = "base"

    def url_root(self):
        return self.URL_ROOT

    def menu_url(self):
        return "/%s/%s" % (self.url_root(), "menu")

    def confirm_url(self, arg=None):
        if arg:
            return "/%s/%s/%s" % (self.url_root(), "confirm", arg)
        else:
            return "/%s/%s" % (self.url_root(), "confirm")

    def confirm_choices(self):
        return Choices("yes (1, yes), no (2, no)")

    def confirm_prompt(self):
        return "Say yes or press 1 for yes. Say no or press 2 for no."

    def response_url(self):
        return "/%s/%s" % (self.url_root(), "response")

    # base class for menu-driven activities
    def POST(self, name, arg=None):
        web.header('Content-Type', 'text/json')
        if name == 'menu':
            return self.do_menu()
        elif name == 'response':
            return self.do_response()
        elif name == 'confirm':
            answer = self.get_answer()
            if answer == 'yes':
                return self.do_confirm_ok(arg)
            else:
                return self.do_bad_choice("Okay, let's try again")
        else:
            raise Exception("don't know how to do action %s" % name)

    def do_bad_choice(self, message="Sorry, that's not a valid choice."):
        t = Tropo()
        t.say(message)
        t.on(event = "continue", next=self.menu_url())
        return t.RenderJson()

class VoteTropo(MenuTropo):
    URL_ROOT = 'vote'

    def do_menu(self):
        t = Tropo()
        prompt = """
        You will shortly be prompted to enter the two digit code for the
        company you want to vote for.  If you already know the code, you can
        enter it at any time using your phone's keypad.
        """
        for candidate in models.get_candidates():
            prompt += "For %s, enter %s. " % (candidate['name'], candidate['vote_code'])

        t.ask(Choices("[2 DIGITS]", mode="dtmf"), say=prompt)
        t.on(event="continue", next=self.response_url())
        return t.RenderJson()

    def do_response(self):
        answer = self.get_answer()
        candidate = models.find_candidate_by_code(answer)

        if not candidate:
            return self.do_bad_choice()
        else:
            t = Tropo()
            prompt = "You chose %s, is that correct? " % candidate['name']
            choices = self.confirm_choices()
            t.ask(choices, say=prompt + self.confirm_prompt())
            t.on(event="continue", next=self.confirm_url(candidate['id']))
            return t.RenderJson()

    def do_confirm_ok(self, candidate_id):
        caller_id = models.caller_id_if_valid(self.call_id())
        models.record_vote(caller_id, candidate_id)
        t = Tropo()
        t.say("Great, your vote has been counted. Goodbye.")
        t.message("Thanks for voting! Tropo <3 you!", channel="TEXT", to=caller_id)
        return t.RenderJson()

class StartTropo(BaseTropo):
    def do_voice(self):
        t = Tropo()
        t.say("Roses are red, violets are blue.")
        t.say("Please vote for the startup that most disrupts you.")

        caller_id = models.caller_id_if_valid(self.call_id())
        if models.caller_id_can_vote(caller_id):
            t.on(event="continue", next="/vote/menu")
        elif not caller_id:
            t.say("Oops, you need to have caller eye dee enabled to vote. Goodbye.")
            t.hangup()
        else:
            t.say("Oops, it looks like you have voted already. Goodbye.")
            t.hangup()

        return t.RenderJson()

    def do_text(self):
        caller_id = models.caller_id_if_valid(self.call_id())
        if models.caller_id_can_vote(caller_id):
            session_info = json.loads(web.data())['session']
            msg = session_info['initialText']
            m = re.match("^(v|V|vote|VOTE)\s+([0-9]{2})$", msg)
            if m:
                vote_code = m.groups()[1]
                candidate = models.find_candidate_by_code(vote_code)
                if candidate:
                    models.record_vote(caller_id, candidate['id'])
                    t = Tropo()
                    t.message(
                            "You have voted for %s as most disruptive startup. Thanks for voting! Tropo <3s you!" % candidate['name'],
                            to=caller_id, channel='TEXT')
                    return t.RenderJson()
                else:
                    return self.do_help_text("Sorry, there's no candidate %s. " % vote_code)
            else:
                return self.do_help_text("Sorry, we didn't understand your text message. ")
        elif not caller_id:
            return self.do_help_text("You need to have caller ID enabled to vote.")
        else:
            t = Tropo()
            t.message("Oops, it looks like you have voted already.", to=caller_id, channel='TEXT')
            return t.RenderJson()

    def do_help_text(self, msg=""):
        caller_id = models.caller_id_if_valid(self.call_id())
        t = Tropo()
        say = "%sPhone this number back to use the voice interface or visit disrupt.pitchlift.org for help." % msg
        t.message(say, to=caller_id, channel="TEXT")
        return t.RenderJson()

    def POST(self):
        # save session info for this call
        session_info = json.loads(web.data())['session']

        tropo_call_id = session_info['callId']
        caller_network = session_info['from']['network']
        caller_channel = session_info['from']['channel']
        caller_id = session_info['from']['id']

        models.new_session(
                tropo_call_id,
                caller_network,
                caller_channel,
                caller_id)

        if caller_channel == 'VOICE':
            return self.do_voice()
        elif caller_channel == 'TEXT':
            return self.do_text()
        else:
            raise Exception("unexpected caller channel %s" % caller_channel)

class Index(BaseTropo):
    def GET(self):
        candidates = models.get_candidates()
        return render.index(candidates)

app = web.application(urls, globals())
application = app.wsgifunc()
