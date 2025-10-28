from crewai.flow.flow import Flow, listen, start, router, and_, or_
from crewai.agent import Agent
from crewai import LLM
from pydantic import BaseModel
from tools import web_search_tool
from seo_crew import SeoCrew
from virality_crew import ViralityCrew

class BlogPost(BaseModel):
    title: str
    subtitle: str
    sections: list[str]

class TweetPost(BaseModel):
    contnet: str
    hashtags: str

class LinkedInPost(BaseModel):
    hook: str
    content: str
    call_to_action: str

class Score(BaseModel):
    score: int = 0
    reason: str = ""

class ContentPipelineState(BaseModel):

    # Inputs
    content_type: str = ""
    topic: str = ""

    # Internal
    max_length: int = 0
    research: str = ""  
    score: Score | None = None

    # Content
    blog_post: BlogPost | None = None
    tweet_post: TweetPost | None = None
    linkedin_post: LinkedInPost | None = None

class ContentPipelineFlow(Flow[ContentPipelineState]):

    @start()
    def init_content_pipeline(self):
        
        if self.state.content_type not in ["tweet", "blog", "linkedin"]:
            return ValueError("The content type is wrong.")

        if self.state.topic == "":
            return ValueError("The topic can't be blank.")

        if self.state.content_type == "tweet":
            self.state.max_length = 150
        elif self.state.content_type == "blog":
            self.state.max_length = 800
        elif self.state.content_type == "linkedin":
            self.state.max_length = 500

    @listen(init_content_pipeline)
    def conduct_research(self):
        researcher = Agent(
            role="Head Researcher",
            backstory="You're like a digital detective who loves digging up fascinating facts and insights. You have a knack for finding the good stuff that others miss.",
            goal=f"Find the most interesting and useful info about {self.state.topic}",
            tools=[web_search_tool],
        )

        self.state.research = researcher.kickoff(
            f"Find the most interesting and useful info about {self.state.topic}"
        )

    @router(conduct_research)
    def conduct_research_router(self):
        content_type = self.state.content_type

        if content_type == "blog":
            return "make_blog"
        elif content_type == "tweet":
            return "make_tweet"
        else:
            return "make_linkedin"
    
    @listen(or_("make_blog", "remake_blog"))
    def handle_make_blog(self):
        blog_post = self.state.blog_post

        llm = LLM(model="openai/gpt-4o-mini", response_format=BlogPost)

        if blog_post is None:
            self.state.blog_post = llm.call(
                f"""
            Make a blog post with SEO practices on the topic {self.state.topic} using the following research:

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        else:
            self.state.blog_post = llm.call(
                f"""
            You wrote this blog post on {self.state.topic}, but it does not have a good SEO score because of {self.state.score.reason} 
            
            Improve it.

            <blog post>
            {self.state.blog_post.model_dump_json()}
            </blog post>

            Use the following research.

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )

    
    @listen(or_("make_tweet", "remake_tweet"))
    def handle_make_tweet(self):
        tweet_post = self.state.tweet_post

        llm = LLM(model="openai/o4-mini", response_format=TweetPost)

        if tweet_post is None:
            self.state.tweet_post = llm.call(
                f"""
            Make a tweet that can go viral on the topic {self.state.topic} using the following research:

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        else:
            self.state.tweet_post = llm.call(
                f"""
            You wrote this tweet on {self.state.topic}, but it does not have a good virality score because of {self.state.score.reason} 
            
            Improve it.

            <tweet>
            {self.state.tweet.model_dump_json()}
            </tweet>

            Use the following research.

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )

        
    
    @listen(or_("make_linkedin", "remake_linkedin"))
    def handle_make_linkedin(self):
        linkedin_post = self.state.linkedin_post

        llm = LLM(model="openai/o4-mini", response_format=LinkedInPost)

        if linkedin_post is None:
             self.state.linkedin_post = llm.call(
                f"""
            Make a linkedin post that can go viral on the topic {self.state.topic} using the following research:

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        else:
             self.state.linkedin_post = llm.call(
                f"""
            You wrote this linkedin post on {self.state.topic}, but it does not have a good virality score because of {self.state.score.reason} 
            
            Improve it.

            <linkedin_post>
            {self.state.linkedin_post.model_dump_json()}
            </linkedin_post>

            Use the following research.

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
    
    @listen(handle_make_blog)
    def check_seo(self):
        result = (
            SeoCrew()
            .crew()
            .kickoff(
                inputs={
                    "topic": self.state.topic,
                    "blog_post": self.state.blog_post.model_dump_json(),
                }
            )
        )
        self.state.score = result.pydantic
    
    @listen(or_(handle_make_tweet, handle_make_linkedin))
    def check_virality(self):
        result = (
            ViralityCrew()
            .crew()
            .kickoff(
                inputs={
                    "topic": self.state.topic,
                    "content_type": self.state.content_type,
                    "content": (
                        self.state.tweet_post
                        if self.state.contenty_type == "tweet"
                        else self.state.linkedin_post
                    ),
                }
            )
        )
        self.state.score = result.pydantic

    @router(or_(check_seo, check_virality))
    def score_router(self):

        content_type = self.state.content_type
        score = self.state.score

        if score.score >= 8:
            return "check_passed"
        else:
            if content_type == "blog":
                return "remake_blog"
            elif content_type == "tweet":
                return "remake_tweet"
            else:
                return "remake_linkedin"
        

    @listen("check_passed")
    def finalize_content(self):
        print("Scoring content")

flow = ContentPipelineFlow()

flow.kickoff(
    inputs={
        "content_type": "tweet",
        "topic": "AI Dog Training",
    },
)