import urllib.request
import praw.exceptions
from vaporpic import *
from praw import *
from threading import Thread
import threading
import configparser
import simplejson
import os
import time
import prawcore.exceptions

config = configparser.RawConfigParser()
config.read("config/config.properties")
username = config.get('user', 'username')
password = config.get('user', 'password')
client_id = config.get('api', 'client_id')
client_secret = config.get('api', 'client_secret')
user_agent = config.get('api', 'user_agent')
live_m3u_dir = config.get('user', 'live_m3u_dir')
log_dir = config.get('log', 'log_dir')
summon_keyword = "!hotlinkbot"


class HotLinkBot(Thread):
    def __init__(self):
        super().__init__()
        self.successful_reply_header = "\nI managed to find the following links for you!\n\n"
        self.reply_footer = "\n***\n^This ^bot ^is ^maintained ^by ^its ^creator ^u/apt-get-schwifty, " \
                            "^documentation ^for ^the ^bot ^can ^be ^found " \
                            "^[here](https://github.com/schwifty42069/hotlinkbot)"
        self.tvod_mp4_reply_header = "\n| Title | Season | Episode | Link | Size |\n|:--:|:--:|:--:|:--:|:--:|"
        self.tvod_dlpage_reply_header = "\n| Title | Season | Episode | Link |\n|:--:|:--:|:--:|:--:|"
        self.movie_page_reply_header = "\n| Title | Link |\n|:--:|:--:|"
        self.movie_hotlink_reply_header = "\n| Title | Link | Quality |\n|:--:|:--:|:--:|"
        self.livetv_reply_header = "\n| Channel | Link |\n|:--:|:--:|"

        self.sub_name = "hlsvillage"
        self.submission_id = "duwfud"
        self.reply_entries = []
        self.channel_codes = ['ABC', 'AE', 'AMC', 'Animal', 'BBCAmerica', 'BET', 'Boomerang', 'Bravo', 'CN', 'CBS',
                              'CMT', 'CNBC', 'CNN', 'Comedy', 'DA', 'Discovery', 'Disney', 'DisneyJr', 'DisneyXD',
                              'DIY', 'E', 'ESPN', 'ESPN2', 'FoodNetwork', 'FoxBusiness', 'FOX', 'FoxNews', 'FS1',
                              'FS2', 'Freeform', 'FX', 'FXMovie', 'FXX', 'GOLF', 'GSN', 'Hallmark', 'HMM', 'HBO',
                              'HGTV', 'History', 'HLN', 'ID', 'Lifetime', 'LifetimeM', 'MLB', 'MotorTrend', 'MSNBC',
                              'MTV', 'NatGEOWild', 'NatGEO', 'NBA', 'NBCSN', 'NBC', 'NFL', 'Nickelodeon',
                              'Nicktoons', 'OWN', 'Oxygen', 'Paramount', 'PBS', 'POP', 'Science', 'Showtime',
                              'StarZ', 'SundanceTV', 'SYFY', 'TBS', 'TCM', 'Telemundo', 'Tennis', 'CWE',
                              'https://weather-lh.akamaihd.net/i/twc_1@92006/master.m3u8', 'TLC', 'TNT', 'Travel',
                              'TruTV', 'TVLand', 'Univision', 'USANetwork', 'VH1', 'WETV']
        self.daemon = True
        self._stop_event = threading.Event()
        self.auth()

    def auth(self):
        self.reddit = Reddit(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        print("\nAuthenticated as {}!\nIs daemon: {}\n".format(self.reddit.user.me(), self.isDaemon()))

    def run(self):
        while True:
            try:
                self.stream_comments()
            except KeyboardInterrupt:
                self.stop()
                return

    def stop(self):
        print("\nStopping..\n")
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def check_for_missed_summons(self):
        submission = self.reddit.submission(id=self.submission_id)
        submission.comments.replace_more(limit=None)
        comments = submission.comments.list()
        id_list = []
        missed_comment_ids = []
        for comment in comments:
            if "!hotlinkbot" in comment.body:
                id_list.append(comment.id)
        if len(self.read_master_comment_log()['comment_ids']) != 0:
            master_log = self.read_master_comment_log()
            for comment_id in id_list:
                if comment_id not in master_log['comment_ids']:
                    missed_comment_ids.append(comment_id)
        else:
            return id_list

        return missed_comment_ids

    @staticmethod
    def read_master_comment_log():
        if os.path.exists("log/comment_log.json"):
            with open("log/comment_log.json", "r") as r:
                return json.loads(r.read())
        else:
            return {"comment_ids": []}

    @staticmethod
    def write_master_comment_log(master_json):
        print("\nUpdating master log...\n")
        with open("log/comment_log.json", "w") as w:
            w.write(simplejson.dumps(master_json, indent=4, sort_keys=True))
            w.close()
            return

    def reply_to_missed_summons(self, missed_ids_list, master_json):
        print("\nReplying to missed summons!\n")
        print("\nAdding {} missed comment to master log..\n".format(len(missed_ids_list)))
        for cid in missed_ids_list:
            comment = self.reddit.comment(id=cid)
            parse_dict = self.build_parse_dict(comment)
            data = self.parse_command_syntax(parse_dict, comment)
            self.scrape_metadata_and_reply(parse_dict, data, comment)
            master_json['comment_ids'].append(cid)
            self.write_master_comment_log(master_json)
            return

    @staticmethod
    def build_parse_dict(comment):
        elements = comment.body.split("; ")
        parse_dict = {}
        for e in elements:
            if summon_keyword not in e:
                key = e.split("=")[0].lower()
                if "channel" not in e:
                    val = e.split("=")[1].strip(";").lower()
                else:
                    val = e.split("=")[1].strip(";")
                parse_dict.update({key: val})
        return parse_dict

    def scrape_metadata_and_reply(self, parse_dict, data, comment):
        if parse_dict['media'] != "live":
            imdb_query = ImdbQuery(parse_dict['title'])
            imdb_query.scrape_title_codes()
            title_code = imdb_query.title_codes[0]
            if parse_dict['media'] == 'tvod':
                size = []
                if isinstance(data[1], list):
                    for link in data[1]:
                        site = urllib.request.urlopen(link)
                        meta = site.info()
                        size.append(int(int(meta._headers[3][1]) / 1024))
                if data[0] == 0:
                    episode_titles = imdb_query.scrape_episode_titles(title_code, parse_dict['season'])
                    if len(episode_titles) == 0:
                        episode_title = "?"
                    else:
                        episode_title = episode_titles[int(parse_dict['episode']) - 1]

                    self.assemble_tvod_reply_entry(parse_dict['title'], parse_dict['season'], episode_title,
                                                   data[1], size, 0)
                    self.build_successful_reply(comment, parse_dict, link_type="dl")
                    return
                elif data[0] == 1:
                    episode_title = imdb_query.scrape_episode_titles(title_code, parse_dict['season'])[int(
                        parse_dict['episode']) - 1]

                    self.assemble_tvod_reply_entry(parse_dict['title'], parse_dict['season'], episode_title,
                                                   data[1], size, 1)
                    self.build_successful_reply(comment, parse_dict, link_type="hot")
                    return
            elif parse_dict['media'] == "movie":
                if data[0] == 0:
                    self.assemble_movie_reply_entry(parse_dict['title'], data[1], 0)
                    self.build_successful_reply(comment, parse_dict, link_type="dl")
                elif data[0] == 1:
                    # noinspection PyTypeChecker
                    self.assemble_movie_reply_entry(parse_dict['title'], data[1]['src'], 1,
                                                    q=data[1]['quality'])
                    self.build_successful_reply(comment, parse_dict, link_type="hot")
                    return
        else:
            self.assemble_livetv_reply(parse_dict['channel'], data)
            self.build_successful_reply(comment, parse_dict)
            return

    def stream_comments(self):
        while True:
            try:
                master_log = self.read_master_comment_log()
                missed_summons = self.check_for_missed_summons()
                if len(master_log['comment_ids']) == 0:
                    master_log.update({"comment_ids": missed_summons})
                    self.write_master_comment_log(master_log)
                    missed_summons.clear()

                else:
                    if len(missed_summons) != 0:
                        self.reply_to_missed_summons(missed_summons, master_log)
                        for cid in missed_summons:
                            master_log['comment_ids'].append(cid)
            except prawcore.exceptions.RequestException:
                print("\nNetwork exception occurred at {}, waiting 10 seconds to retry..\n".format(time.ctime()))
                time.sleep(10)
                continue

            try:
                print("\nStreaming comments...\n")
                for comment in self.reddit.subreddit(self.sub_name).stream.comments(skip_existing=True):
                    if summon_keyword in comment.body:
                        print("\nBot was summoned via comment!\n")
                        parse_dict = self.build_parse_dict(comment)
                        if parse_dict['media'] != "live":
                            parse_dict = self.parse_out_characters(parse_dict)
                        data = self.parse_command_syntax(parse_dict, comment)
                        if data is None:
                            self.reply_with_error(0, comment, parse_dict)
                        elif data == -1:
                            self.reply_with_error(1, comment, parse_dict)
                        else:
                            self.scrape_metadata_and_reply(parse_dict, data, comment)
                        master_log = self.read_master_comment_log()
                        print("\nCurrent log length is {}\n".format(len(master_log['comment_ids'])))
                        master_log['comment_ids'].append(comment.id)
                        self.write_master_comment_log(master_log)
            except prawcore.exceptions.RequestException:
                print("\nNetwork exception occurred at {}, waiting 10 seconds to retry..\n".format(time.ctime()))
                time.sleep(10)

    @staticmethod
    def parse_out_characters(parse_dict):
        # This method is just for parsing out troublesome chars
        chars = [":", ".", ",", "-"]
        if "title" in parse_dict.keys():
            for c in chars:
                if c in parse_dict['title']:
                    t_words = parse_dict['title'].split(c)
                    new_title = ""
                    for w in t_words:
                        new_title += w
                    parse_dict.update({"title": new_title})
            return parse_dict

    def parse_command_syntax(self, parse_dict, comment):
        print("\nParse dict: {}\n".format(parse_dict))
        if parse_dict['media'] == "tvod" and "season" not in parse_dict.keys() or parse_dict['media'] == "tvod" and \
                "episode" not in parse_dict.keys():
            self.reply_with_error(1, comment, parse_dict)
            return
        if parse_dict['media'] == "live" and "channel" not in parse_dict.keys():
            self.reply_with_error(1, comment, parse_dict)
            return
        if parse_dict['media'] == "tvod":
            imdb_query = ImdbQuery(parse_dict['title'])
            imdb_query.scrape_title_codes()
            w = WatchEpisodeApi(parse_dict['title'], parse_dict['season'], parse_dict['episode'])
            ref_link = w.fetch_ref_link()
            try:
                source_links = w.build_source_link_list(ref_link)
                if source_links == -1:
                    return -1
                hotlinks = w.scrape_hotlinks(source_links)

                if len(hotlinks) == 0:
                    va = VidnodeApi(parse_dict['media'], parse_dict['title'], s=parse_dict['season'],
                                    e=parse_dict['episode'])
                    search = va.assemble_search_url()
                    media_url = va.assemble_media_url(search)
                    dl_page = va.scrape_final_links(media_url, True)
                    if dl_page is None:
                        return
                    return [0, dl_page]
                else:
                    return [1, hotlinks]
            except requests.exceptions.MissingSchema:
                self.reply_with_error(0, comment, parse_dict)
                return

        if parse_dict['media'] == "movie":
            print("\nTrying SimpleMovieApi...\n")
            sma = SimpleMovieApi(parse_dict['title'])
            result = sma.check_for_movie()
            if result != -1:
                return [1, result]
            else:
                try:
                    print("\nFailed to find with SimpleMovieApi, trying VidnodeApi...\n")
                    va = VidnodeApi(parse_dict['media'], parse_dict['title'])
                    search = va.assemble_search_url()
                    media_url = va.assemble_media_url(search)
                    dl_page = va.scrape_final_links(media_url, True)
                    if dl_page is None:
                        return
                    return [0, dl_page]
                except TypeError:
                    return

        if parse_dict['media'] == "live":
            if parse_dict['channel'] not in self.channel_codes:
                self.reply_with_error(2, comment, parse_dict)
            else:
                with open(live_m3u_dir, "r") as r:
                    for line in r.readlines():
                        if "{}/myStream".format(parse_dict['channel']) in line:
                            return line
                        else:
                            continue

    def assemble_tvod_reply_entry(self, title, season, episode, link, size, link_type):
        if link_type == 1:
            for l, s in zip(link, size):
                if l not in self.reply_entries and "http" in l and "mp4" in l:
                    s = int(s) / 1000
                    self.reply_entries.append('\n| {} | {} | {} | {} | {} |'.format(
                        title, season, episode, "[mp4 hotlink]({})".format(l), "{}mb".format(str(s))))
        elif link_type == 0:
            self.reply_entries.append('\n| {} | {} | {} | {} |'.format(
                title, season, episode, "[download page]({})".format(link)))

    def assemble_movie_reply_entry(self, title, link, link_type, **kwargs):
        if link_type == 1:
            q = kwargs.get('q')
            self.reply_entries.append('\n| {} | {} | {} |'.format(title, "[m3u8 hotlink]({})".format(link), q))
        elif link_type == 0:
            self.reply_entries.append('\n| {} | {} |'.format(title, "[download page]({})".format(link)))

    def assemble_livetv_reply(self, channel, link):
        self.reply_entries.append('\n| {} | {} |'.format(channel, "[link]({})".format(link.strip("\n"))))

    def build_successful_reply(self, comment, parse_dict, **kwargs):
        reply = ""
        header = ""
        if parse_dict['media'] == "tvod":
            if kwargs.get("link_type") == "hot":
                header = self.tvod_mp4_reply_header
            else:
                header = self.tvod_dlpage_reply_header
        elif parse_dict['media'] == "movie":
            if kwargs.get('link_type') == "dl":
                header = self.movie_page_reply_header
            elif kwargs.get('link_type') == "hot":
                header = self.movie_hotlink_reply_header
        elif parse_dict['media'] == "live":
            header = self.livetv_reply_header
        reply += self.successful_reply_header
        reply += header
        for entry in self.reply_entries:
            reply += entry
        reply += self.reply_footer
        sent = False
        while not sent:
            try:
                comment.reply(reply)
                sent = True
                print("\nSending reply:\n{}\n".format(reply))
                self.reply_entries.clear()
            except praw.exceptions.APIException:
                continue
        bl = BotLogger(time.ctime(), str(comment.author), parse_dict, True)
        bl.write_log()

    @staticmethod
    def reply_with_error(error_type, comment, parse_dict):
        reply = ""
        print("\nReplying with an error!\n")
        sent = False
        while not sent:
            try:
                if error_type == 0:
                    reply = "Sorry, I was unable to find a link for the specified title! ):"
                    comment.reply(reply)
                elif error_type == 1:
                    reply = "Sorry, I couldn't understand your request because a required argument is missing!"
                    comment.reply(reply)
                elif error_type == 2:
                    reply = "Sorry, this bot doesn't support a channel with that name! ):"
                    comment.reply(reply)
                print("\nSending reply:\n{}\n".format(reply))
                sent = True
            except praw.exceptions.APIException:
                continue
        bl = BotLogger(time.ctime(), str(comment.author), parse_dict, False)
        bl.write_log()


class BotLogger(object):
    def __init__(self, log_time, author, data, success):
        self.log_dir = log_dir
        self.log_time = log_time
        self.author = author
        self.data = data
        if data['media'] == "movie":
            self.log_template = {self.author: [{"time": self.log_time, "media_type": self.data['media'],
                                                "title": self.data['title'], "success": success}]}
        elif data['media'] == "tvod":
            if "episode" not in data.keys():
                self.log_template = {self.author: [{"time": self.log_time, "media_type": self.data['media'],
                                                    "title": self.data['title'], "season": self.data['season'],
                                                    "success": success}]}
            elif "season" not in data.keys():
                self.log_template = {self.author: [{"time": self.log_time, "media_type": self.data['media'],
                                                    "title": self.data['title'], "episode": self.data['episode'],
                                                    "success": success}]}
            else:
                self.log_template = {self.author: [{"time": self.log_time, "media_type": self.data['media'],
                                                    "title": self.data['title'], "season": self.data['season'],
                                                    "episode": self.data['episode'], "success": success}]}
        else:
            if "channel" not in data.keys():
                self.log_template = {self.author: [{"time": self.log_time, "media_type": self.data['media'],
                                                    "success": success}]}
            else:
                self.log_template = {self.author: [{"time": self.log_time, "media_type": self.data['media'],
                                                    "channel": self.data['channel'], "success": success}]}

    def write_log(self):
        if not os.path.exists(self.log_dir):
            with open(self.log_dir, "w") as w:
                w.write(simplejson.dumps(self.log_template, indent=4, sort_keys=True))
                w.close()
        else:
            with open(self.log_dir, "r") as r:
                current_log = json.loads(r.read())
                r.close()
            if self.author in current_log.keys():
                current_log[self.author].append(self.log_template[self.author])
                with open(self.log_dir, "w") as w:
                    w.write(simplejson.dumps(current_log, indent=4, sort_keys=True))
                    w.close()
            else:
                current_log.update(self.log_template)
                with open(self.log_dir, "w") as w:
                    w.write(simplejson.dumps(current_log, indent=4, sort_keys=True))
                    w.close()




