#! /usr/bin/env python

import os
import sys

sadm_path = os.path.join( os.environ['HOME'], 'sadm' )
sys.path.append( sadm_path )
sys.path.append( os.path.join( sadm_path, 'lib' ) )
sys.path.append( os.path.join( sadm_path, 'buildscripts' ) )

import ircbot
import irclib
import command

import sadm_config
import buildinfo

SADM_CHANNEL = '#sadm'
AUTHORIZED_NICKS = [ 'psbot' ]
IRC_SERVER = 'bazaar.example.com' ## TODO make me part of a conf...
IRC_PORT = 6667
IRC_PASSWORD = 'password' # TODO make me part of a conf...
DEFAULT_NICK = 'unnamed-box'

class SadmBot(ircbot.SingleServerIRCBot):
    def __init__(self, channels, nickname, server, port=6667, password=None, ssl=False):
        if password is None:
            ircbot.SingleServerIRCBot.__init__(self, 
                                               [(server,port)], 
                                               "[%s]" % nickname, 
                                               "[%s]" % nickname, ssl=ssl)
        else:
            ircbot.SingleServerIRCBot.__init__(self, 
                                               [(server, port, password)],
                                               "[%s]" % nickname, 
                                               "[%s]" % nickname, ssl=ssl)
        self.join_channels = channels
        self.nickname = nickname
        self.authorized_nicks = set()
        self.cmds_run = 0

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        for channel in self.join_channels:
            c.join(channel)
        c.privmsg( SADM_CHANNEL, "#%s is ready" % (self.nickname) )
        self.refresh_users()

    def on_privmsg(self, c, e):
        self.do_cmd(e, e.arguments()[0], self.nickname)

    def on_pubmsg(self, c, e):
        src_nick = e.source().split('!')[0]
        if self.cmds_run % 10 == 0:
            self.refresh_users()

        a = e.arguments()[0].split(":", 1)
        if len(a) > 1 and irclib.irc_lower(a[0]) == irclib.irc_lower(self.connection.get_nickname()):
            cmd = a[1].strip()
            addressed_to=self.nickname
        elif e.arguments()[0].startswith( "%s:" % self.nickname ):
            cmd = a[-1].strip()
            addressed_to=self.nickname
        elif e.arguments()[0].startswith( "all:"):
            cmd = a[-1].strip()
            addressed_to='all'
        elif e.target().lower() == "#%s" % self.nickname.lower() and e.arguments()[0].startswith('~'):
            cmd = e.arguments()[0][1:].strip()
            addressed_to=self.nickname
        else:
            cmd = None
            addressed_to = None

        if cmd is not None and src_nick in self.authorized_nicks:
            self.cmds_run += 1
            self.do_cmd(e, cmd, addressed_to=addressed_to )
        elif cmd is not None:
            #c.notice( self.authorized_nicks[0], "%s is bothering me!" % src_nick )
            c.privmsg( SADM_CHANNEL, "~lart %s for bothering me" % src_nick )
            print( "%s is bothering me!" % src_nick )

    def on_dccmsg(self, c, e):
        c.privmsg("You said: " + e.arguments()[0])

    def on_dccchat(self, c, e):
        if len(e.arguments()) != 2:
            return
        args = e.arguments()[1].split()
        if len(args) == 4:
            try:
                address = irclib.ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def run_cmd( self, nick, cmd ):
        print( "%s: running %s" % ( nick, cmd ) )
        #self.connection.privmsg( SADM_CHANNEL, "%s: Starting cmd %s" % (nick, cmd.split()[0]) )
        cmd_obj = command.Command( cmd )
        #self.connection.privmsg( SADM_CHANNEL, "%s: %s returned." % ( nick, cmd.split()[0]) )
        output = cmd_obj.get_output()
        while output is not None:
            print( "Recieved: %s" % output )
            self.connection.privmsg( '#%s' % self.nickname, "%s: %s" % ( nick, output ) )
            output = cmd_obj.get_output()
        result = cmd_obj.wait()
        self.connection.privmsg( '#%s' % self.nickname, "%s: %s returned: %s" % ( nick, cmd.split()[0], result ) )
        return (result, nick, cmd)

    def get_sandboxes( self ):
        sbs=[]
        sbs_folder = sadm_config.Config().sandbox_container_folder
        for i in os.listdir( sbs_folder ):
            if os.path.isdir(os.path.join( sbs_folder, i )) and i.count('.') >= 2:
                sbs.append( i )
        return sbs

    def do_cmd(self, e, cmd, addressed_to):
        nick = irclib.nm_to_n(e.source())
        c = self.connection
        cmd_segs = cmd.split(' ')
        c.privmsg( SADM_CHANNEL, "%s: %s output in #%s" % ( nick, cmd, self.nickname ) )
        c.privmsg( '#%s' % self.nickname, "%s: Running %s" % ( nick, cmd ) )

        print( "log: %s %s %s %s" % ( repr(e.arguments()), repr(e.eventtype()), repr(e.source()), repr(e.target()) ) )

        if cmd == "disconnect":
            ### Kick everyone out of my private channel ###
            for i in self.channels['#%s' % self.nickname].users():
                c.kick( '#%s' % self.nickname, i, "Goodbye, the server is leaving the channel." )
            self.disconnect()
        elif cmd == "die":
            ### Kick everyone out of my private channel ###
            for i in self.channels['#%s' % self.nickname].users():
                c.kick( '#%s' % self.nickname, i, "Goodbye, the server is leaving the channel." )
            self.die()
        elif cmd_segs[0] == "sadm":
            if len(cmd_segs) < 2 or cmd_segs[1] in ['config', 'foreach', 'loop']:
                c.privmsg( "#%s" % self.nickname, "%s: I don't want to do that." % nick )
                c.kick( e.target(), nick, "Go away." )
                return
            self.run_cmd( nick, cmd + ' --no-color' )
        elif cmd_segs[0] == "bzr":
            c.privmsg( "#%s" % self.nickname, "%s: bzr cmds are not implemented." % nick )
        elif cmd_segs[0] == "sb":
            c.privmsg( "#%s" % self.nickname, "%s: sb cmds are not implemented." % nick )
        elif cmd_segs[0] == "sysinfo":
            c.privmsg( "#%s" % self.nickname, "%s: sysinfo cmds are not implemented." % nick )
        elif cmd_segs[0].lower() == "exists":
            print( "%s: %s" % ( nick, cmd ) )
            if len( cmd_segs ) < 3:
                c.notice( nick, "Usage: <machine>: exists [branch|component|type|sandbox] <name>" )
                print( "cmd_segs: %s" % repr( cmd_segs ) )
            elif cmd_segs[1] == "branch":
                branches = set([ x.split('.')[1] for x in self.get_sandboxes() ])
                if cmd_segs[-1] in branches:
                    c.privmsg( "#%s" % self.nickname, "%s: %s has %s" % ( nick, self.nickname, cmd_segs[-1] ) )
                elif addressed_to != "all":
                    c.privmsg( "#%s" % self.nickname, "%s: %s does not have %s" % ( nick, self.nickname, cmd_segs[-1] ) )
            elif cmd_segs[1] == "component":
                branches = set([ x.split('.')[0] for x in self.get_sandboxes() ])
                if cmd_segs[-1] in branches:
                    c.privmsg( "#%s" % self.nickname, "%s: %s has %s" % ( nick, self.nickname, cmd_segs[-1] ) )
                elif addressed_to != "all":
                    c.privmsg( "#%s" % self.nickname, "%s: %s does not have %s" % ( nick, self.nickname, cmd_segs[-1] ) )
            elif cmd_segs[1] == "type":
                branches = set([ x.split('.')[2] for x in self.get_sandboxes() ])
                if cmd_segs[-1] in branches:
                    c.privmsg( "#%s" % self.nickname, "%s: %s has %s" % ( nick, self.nickname, cmd_segs[-1] ) )
                elif addressed_to != "all":
                    c.privmsg( "#%s" % self.nickname, "%s: %s does not have %s" % ( nick, self.nickname, cmd_segs[-1] ) )
            elif cmd_segs[1] == "sandbox":
                sbs = self.get_sandboxes()
                if cmd_segs[-1] in sbs:
                    c.privmsg( "#%s" % self.nickname, "%s: %s has %s" % ( nick, self.nickname, cmd_segs[-1] ) )
                elif addressed_to != "all":
                    c.privmsg( "#%s" % self.nickname, "%s: %s does not have %s" % ( nick, self.nickname, cmd_segs[-1] ) )
        elif cmd_segs[0].lower() == "remove":
            c.privmsg( "#%s" % self.nickname, "%s: remove is not implemented." )
        elif cmd_segs[0].lower() == "list":
            print( "%s: %s" % ( nick, cmd ) )
            if len( cmd_segs ) < 2:
                c.notice( nick, "Usage: <machine>: list [branches|components|types|sandboxes]" )
            elif cmd_segs[1] == "branches":
                branches = set([ x.split('.')[1] for x in self.get_sandboxes() ])
                for branch in branches:
                    c.privmsg( '#%s' % self.nickname, "%s: %s" % ( nick, branch ) )
                if len(branches) == 0:
                    c.privmsg( '#%s' % self.nickname, "%s: None" % (nick) )
            elif cmd_segs[1] == "components":
                branches = set([ x.split('.')[0] for x in self.get_sandboxes() ])
                for branch in branches:
                    c.privmsg( '#%s' % self.nickname, "%s: %s" % ( nick, branch ) )
                if len(branches) == 0:
                    c.privmsg( '#%s' % self.nickname, "%s: None" % (nick) )
            elif cmd_segs[1] == "types":
                branches = set([ x.split('.')[2] for x in self.get_sandboxes() ])
                for branch in branches:
                    c.privmsg( '#%s' % self.nickname, "%s: %s" % ( nick, branch ) )
                if len(branches) == 0:
                    c.privmsg( '#%s' % self.nickname, "%s: None" % (nick) )
            elif cmd_segs[1] == "sandboxes":
                sbs = self.get_sandboxes()
                for s in sbs:
                    c.privmsg( '#%s' % self.nickname, "%s: %s" % ( nick, s ) )
                if len(sbs) == 0:
                    c.privmsg( '#%s' % self.nickname, "%s: None" % (nick) )
              
        elif cmd == "stats":
            c.privmsg(e.target(), "%s: Channels: %s" % (nick, repr(self.join_channels)))
            c.privmsg(e.target(), "%s: Authorized: %s" % (nick, repr(self.authorized_nicks)))
            c.privmsg(e.target(), "%s: Commands Run: %s" % (nick, repr(self.cmds_run)))
        #elif cmd == "dcc":
        #    dcc = self.dcc_listen()
        #    c.ctcp("DCC", nick, "CHAT chat %s %d" % (
        #        irclib.ip_quad_to_numstr(dcc.localaddress),
        #        dcc.localport))
        elif cmd_segs[0].lower() == "authorize" and cmd_segs[-1] != "authorize":
            self.authorized_nicks.add( cmd_segs[-1] )
        elif cmd_segs[0].lower() == "unauthorize" and cmd_segs[-1] != "unauthorize":
            if cmd_segs[-1] in self.authorized_nicks and cmd_segs[-1] not in AUTHORIZED_NICKS:
                self.authorized_nicks.remove( cmd_segs[-1] )
        elif cmd_segs[0].lower() == "users":
            return_users = [ x for x in self.authorized_nicks if x in self.channels[SADM_CHANNEL].users() ]
            c.privmsg( e.target(), "I will only listen to %s" % repr( return_users ) )
        elif cmd_segs[0].lower() == "refreshusers":
            self.refresh_users()
        elif cmd_segs[0].lower() == "help":
            c.privmsg( e.target(), "%s: list, exists, sadm, refreshusers, bzr, sb, ..." % nick )
        else:
            c.privmsg( e.target(), "%s: what is %s?" % (nick, cmd) )

    def refresh_users(self):
        if not "psbot" in self.authorized_nicks:
            self.authorized_nicks.add( 'psbot' )
        if not SADM_CHANNEL in self.channels:
            return
        for i in self.channels[SADM_CHANNEL].users():
            if self.channels[SADM_CHANNEL].is_voiced(i) or self.channels[SADM_CHANNEL].is_oper(i) and i not in self.authorized_nicks:
                self.authorized_nicks.add(i)
        for i in self.authorized_nicks:
            print( "%s (voice: %s, op: %s)" % ( i, self.channels[SADM_CHANNEL].is_voiced(i), self.channels[SADM_CHANNEL].is_oper(i) ) )


def main():
    #server = '10.10.10.100'
    #port = 6667
    server = IRC_SERVER
    port = IRC_PORT

    build_info = buildinfo.BuildInfo()

    print( "Build Info: %s" % repr( (build_info.os, build_info.host, build_info.version, build_info.bitness, build_info.stamp) ) )

    nickname = sys.argv[-1]
    if len(sys.argv) <= 1:
        nickname = build_info.host

    if nickname == "localhost":
        nickname = DEFAULT_NICK

    channels = [SADM_CHANNEL, '#%s' % nickname ]
    password = IRC_PASSWORD

    print( "Starting %s on %s:%s %s" % ( nickname, server, port, channels ) )
    bot = SadmBot(channels, nickname, server, port, password, ssl=True)
    bot.start()

if __name__ == "__main__":
    main()
