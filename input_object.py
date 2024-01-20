
class InputObject:
    def __init__(self,media,reddit_url,type,caption,subreddit,parse_mode="HTML"):
        self.media = media
        self.reddit_url=reddit_url
        self.type=type
        self.caption=caption
        self.subreddit=subreddit
        self.parse_mode=parse_mode


        # self.caption=f'"{self.title}"\n <a href="{self.reddit_url}">r/{self.subreddit}</a>\n\n{self.chat_id}'
