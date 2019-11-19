import praw.exceptions
from vaporpic import *
from praw import *
from threading import Thread
import threading
import configparser

config = configparser.RawConfigParser()
config.read("config/config.properties")
username = config.get('user', 'username')
password = config.get('user', 'password')
client_id = config.get('api', 'client_id')
client_secret = config.get('api', 'client_secret')
user_agent = config.get('api', 'user_agent')
live_m3u_dir = config.get('user', 'live_m3u_dir')
summon_keyword = "!hotlinkbot"


class HotLinkBot(Thread):
    def __init__(self):
        super().__init__()
        self.successful_reply_header = "\nI managed to find the following links for you!\nc\n"
        self.reply_footer = "\n***\n^This ^bot ^is ^maintained ^by ^its ^creator ^u/apt-get-schwifty, " \
                            "^documentation ^for ^the ^bot ^can ^be ^found " \
                            "^[here](https://github.com/schwifty42069/hotlinkbot)"
        self.tvod_reply_header = "\n| Title | Season | Episode | Link |\n|:--:|:--:|:--:|:--:|"
        self.movie_page_reply_header = "\n| Title | Link |\n|:--:|:--:|"
        self.movie_hotlink_reply_header = "\n| Title | Link | Quality |\n|:--:|:--:|:--:|"
        self.livetv_reply_header = "\n| Channel | Link |\n|:--:|:--:|"

        self.sub_name = "hlsvillage"
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
                self.build_parse_dict()
            except KeyboardInterrupt:
                self.stop()
                return

    def stop(self):
        print("\nStopping..\n")
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def build_parse_dict(self):
        print("\nStreaming comments...\n")
        parse_dict = {}
        for comment in self.reddit.subreddit(self.sub_name).stream.comments(skip_existing=True):
            if summon_keyword in comment.body:
                print("\nBot was summoned via comment!\n")
                elements = comment.body.split("; ")
                for e in elements:
                    if summon_keyword not in e:
                        key = e.split("=")[0]
                        val = e.split("=")[1].strip(";")
                        parse_dict.update({key: val})
                parse_dict = self.parse_out_characters(parse_dict)
                data = self.parse_command_syntax(parse_dict, comment)
                if data is None:
                    parse_dict.clear()
                    continue
                else:
                    if parse_dict['media'] != "live":
                        imdb_query = ImdbQuery(parse_dict['title'])
                        imdb_query.scrape_title_codes()
                        title_code = imdb_query.title_codes[0]
                        if parse_dict['media'] == 'tvod':
                            if data[0] == 0:
                                episode_title = imdb_query.scrape_episode_titles(title_code, parse_dict['season'])[int(
                                    parse_dict['episode']) - 1]
                                self.assemble_tvod_reply_entry(parse_dict['title'], parse_dict['season'], episode_title,
                                                               data[1], 0)
                                self.build_successful_reply(comment, parse_dict['media'])
                            elif data[0] == 1:
                                episode_title = imdb_query.scrape_episode_titles(title_code, parse_dict['season'])[int(
                                    parse_dict['episode']) - 1]
                                self.assemble_tvod_reply_entry(parse_dict['title'], parse_dict['season'], episode_title,
                                                               data[1], 1)
                                self.build_successful_reply(comment, parse_dict['media'])
                        elif parse_dict['media'] == "movie":
                            if data[0] == 0:
                                self.assemble_movie_reply_entry(parse_dict['title'], data[1], 0)
                                self.build_successful_reply(comment, parse_dict['media'], link_type="dl")
                            elif data[0] == 1:
                                # noinspection PyTypeChecker
                                self.assemble_movie_reply_entry(parse_dict['title'], data[1]['src'], 1,
                                                                q=data[1]['quality'])
                                self.build_successful_reply(comment, parse_dict['media'], link_type="hot")

                        parse_dict.clear()
                    else:
                        self.assemble_livetv_reply(parse_dict['channel'], data)
                        self.build_successful_reply(comment, parse_dict['media'])
                        parse_dict.clear()

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
        # Making sure key/val pairs are lowercase
        key_list = []
        val_list = []
        for key, val in zip(parse_dict.keys(), parse_dict.values()):
            key = key.lower()
            val = val.lower()
            key_list.append(key)
            val_list.append(val)
        parse_dict.clear()
        for key, val in zip(key_list, val_list):
            parse_dict.update({key: val})
        print("\nParse dict: {}\n".format(parse_dict))
        if parse_dict['media'] == "tvod" and "season" not in parse_dict.keys() or parse_dict['media'] == "tvod" and \
                "episode" not in parse_dict.keys():
            self.reply_with_error(1, comment)
            return
        if parse_dict['media'] == "live" and "channel" not in parse_dict.keys():
            self.reply_with_error(1, comment)
            return
        if parse_dict['media'] == "tvod":
            imdb_query = ImdbQuery(parse_dict['title'])
            imdb_query.scrape_title_codes()
            w = WatchEpisodeApi(parse_dict['title'], parse_dict['season'], parse_dict['episode'])
            ref_link = w.fetch_ref_link()
            try:
                source_links = w.build_source_link_list(ref_link)
                hotlinks = w.scrape_hotlinks(source_links)

                if len(hotlinks) == 0:
                    va = VidnodeApi(parse_dict['media'], parse_dict['title'], s=parse_dict['season'],
                                    e=parse_dict['episode'])
                    search = va.assemble_search_url()
                    media_url = va.assemble_media_url(search)
                    dl_page = va.scrape_final_links(media_url, True)
                    return [0, dl_page]
                else:
                    return [1, hotlinks]
            except requests.exceptions.MissingSchema:
                self.reply_with_error(0, comment)

        if parse_dict['media'] == "movie":
            print("\nTrying SimpleMovieApi...\n")
            sma = SimpleMovieApi(parse_dict['title'])
            result = sma.check_for_movie()
            if result != -1:
                return [1, result]
            else:
                print("\nFailed to find with SimpleMovieApi, trying VidnodeApi...\n")
                va = VidnodeApi(parse_dict['media'], parse_dict['title'])
                search = va.assemble_search_url()
                media_url = va.assemble_media_url(search)
                dl_page = va.scrape_final_links(media_url, True)
                return [0, dl_page]

        if parse_dict['media'] == "live":
            if parse_dict['channel'] not in self.channel_codes:
                self.reply_with_error(2, comment)
            else:
                with open(live_m3u_dir, "r") as r:
                    for line in r.readlines():
                        if "{}/myStream".format(parse_dict['channel']) in line:
                            return line
                        else:
                            continue

    def assemble_tvod_reply_entry(self, title, season, episode, link, link_type):
        if link_type == 1:
            for l in link:
                if l not in self.reply_entries and "http" in l:
                    self.reply_entries.append('\n| {} | {} | {} | {} |'.format(
                        title, season, episode, "[mp4 hotlink]({})".format(l)))
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

    def build_successful_reply(self, comment, media, **kwargs):
        reply = ""
        header = ""
        if media == "tvod":
            header = self.tvod_reply_header
        elif media == "movie":
            if kwargs.get('link_type') == "dl":
                header = self.movie_page_reply_header
            elif kwargs.get('link_type') == "hot":
                header = self.movie_hotlink_reply_header
        elif media == "live":
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

    @staticmethod
    def reply_with_error(error_type, comment):
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
                elif error_type == 3:
                    reply = "I found the requested title, but it looks like the host is still encoding it, please " \
                            "try again later!"
                    comment.reply(reply)
                print("\nSending reply:\n{}\n".format(reply))
                sent = True
            except praw.exceptions.APIException:
                continue
