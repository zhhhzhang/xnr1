# -*-coding: utf-8-*-

import json
import urllib2

import time

from sina.weibo_feedback_follow import FeedbackFollow
from tools.ElasticsearchJson import executeES
from tools.Launcher import SinaLauncher
from tools.HtmlExtractor import extractForHTML
from tools.Pattern import getMatchList, getMatch
from tools.URLTools import getUrlToPattern
from tools.TimeChange import getTimeStamp


class FeedbackLike:
    def __init__(self, uid, current_ts, fans, follow):
        self.uid = uid
        #followType = FeedbackFollow(uid, current_ts)
        self.follow = follow
        self.fans = fans
        self.update_time = current_ts

    def likeInbox(self):
        cr_url = 'http://weibo.com/like/inbox?page=1&&pids=Pl_Content_LikeList'
        json_list = []

        comment_url = cr_url
        while True:
            print comment_url
            try:
                request = urllib2.Request(comment_url)
                response = urllib2.urlopen(request, timeout=60)
                html = response.read().decode('string_escape').replace('\\/', '/')
            except Exception, e:
                print "Network Exception!!! ", e
            finally:
                datas = getMatchList(html, '<div class="WB_feed_detail clearfix">(*)<!--/主评论-->')
                # print len(datas)

                for data in datas:
                    photo_url = "http:" + getMatch(data, '<img.*?src="(*)"')
                    uid = getMatch(data, 'usercard="id=(*)"')
                    nickname = getMatch(data, 'usercard=.*?alt="(*)"')
                    mid = getMatch(data, '&cid=(*)&')
                    timestamp = getMatch(data, '<div class="WB_from S_txt2">(*)  来自')
                    if timestamp:
                        timestamp = long(getTimeStamp(timestamp))
                    else:
                        timestamp = 0

                    text = getMatch(data, '<div class="WB_text S_txt2">(*)</div>')
                    if text:
                        text = extractForHTML(text)
                    else:
                        text = ''
                    r_mid = getMatch(data, 'mid=(*)&')
                    r_uid = self.uid

                    _type = 'stranger'
                    type1 = ''
                    type2 = ''
                    for fljson in self.follow:
                        fjson = json.loads(fljson)
                        if fjson['uid'] == uid:
                            type1 = 'follow'
                            break
                    for fljson in self.fans:
                        fjson = json.loads(fljson)
                        if fjson['uid'] == uid:
                            type2 = 'followed'
                            break
                    if type1 and type2:
                        _type = 'friend'
                    elif type1:
                        _type = type1
                    elif type2:
                        _type = type2
                    if uid == r_uid:
                        _type = 'self'

                    wb_item = {
                        'photo_url': photo_url,
                        'uid': uid,
                        'nick_name': nickname,
                        'mid': mid,
                        'timestamp': timestamp,
                        'text': text,
                        'root_mid': r_mid,
                        'root_uid': r_uid,
                        'weibo_type': _type,#,
                        'update_time':self.update_time#,
                        #'update_time': int(round(time.time()))
                    }

                    wb_json = json.dumps(wb_item)
                    json_list.append(wb_json)

                # 分页
                next_pageUrl = getUrlToPattern(html, comment_url, pattern='page', text_pattern='下一页')
                # print next_pageUrl
                if next_pageUrl:
                    comment_url = next_pageUrl[0]
                else:
                    break
        return json_list

    def execute(self):
        list = self.likeInbox()
        executeES('weibo_feedback_like', 'text', list)


if __name__ == '__main__':
    xnr = SinaLauncher('', '')
    xnr.login()
    FeedbackLike(xnr.uid).execute()
