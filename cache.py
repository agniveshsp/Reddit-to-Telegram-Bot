import json


class Cache:
    """
    Class that handles saving and reading of json files in the /cache folder.
    """

    @staticmethod
    def is_a_repost(subreddit:str,post_id:str):
        """
        Checks if the fetched post has been sent as a message before.

        Args:
            subreddit(str): name of the subreddit
            post_id(str): unique id of the post.

        Returns:
            bool: True if repost, else False.

        """
        subreddit=subreddit.lower()

        try:
            with open(f"cache/{subreddit}.json","r") as datafile:
                 cache_data = json.load(datafile)

        except (FileNotFoundError, json.JSONDecodeError):
            #Reset the cache file
            with open(f"cache/{subreddit}.json", "w") as datafile:
                new_data = {subreddit: []}
                json.dump(new_data, datafile, indent=4)
            return False

        else:#Search if post_id already exits.
             if post_id in cache_data[subreddit]:
                return True
             else:
                 return False

    @staticmethod
    def save_post_id(subreddit,post_id): #new Json for each subreddit in list
        """
        Stores the fetched post id into a json file to prevent reposts.

        Args:
            subreddit(str): name of the subreddit
            post_id(str): unique id of the post.

        Returns:
            None

        """
        subreddit = subreddit.lower()
        try:
            with open(f"cache/{subreddit}.json", "r") as datafile:
                new_data = (json.load(datafile))

        except:# error in loading.
            with open(f"cache/{subreddit}.json","w")as datafile:
                new_data= {subreddit:[]}
                json.dump(new_data,datafile,indent=4)

        finally:
            with open(f"cache/{subreddit}.json","w")as datafile:
                new_data[subreddit].append(post_id)
                json.dump(new_data, datafile, indent=4)



