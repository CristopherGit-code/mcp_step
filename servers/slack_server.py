from typing import Any
from slack_sdk import WebClient
from modules.config import Settings
from mcp.server.fastmcp import FastMCP
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
from modules.oci_client import Client
from dotenv import load_dotenv

mcp = FastMCP("Slack")

class Storage:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Storage, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not Storage._initialized:
            load_dotenv()
            self.merged_data = ''
            self.settings = Settings("mcp.yaml")
            self.slack_client = WebClient(token=self.settings.slack_app.bot_key)
            self.slack_user = WebClient(token=self.settings.slack_app.user_lv_key)
            self.llm_client = Client(self.settings)
            Storage._initialized = True

def get_user_name(user_id:str = None) -> str:
    if not user_id:
        return 'No user provided'
    
    try:
        slack_client = Storage().slack_client
        data = slack_client.users_info(user=user_id)
        profile = data['user']['profile']
        display_name = profile.get('display_name') or profile.get('real_name') or user_id
        return display_name
    except SlackApiError as s:
        return f'Failed fetching user name: error {s}'
    
def get_ch_messages(channel_id:str = None, days:int = 1) -> list[Any]:    
    now = datetime.now()
    past_days = now-timedelta(days=days)
    timestamp = str(past_days.timestamp())
    
    messages = []
    cursor = None
    limit = 1000

    while len(messages)<limit:
        try:
            slack_user = Storage().slack_user
            data = slack_user.conversations_history(
                channel=channel_id,
                oldest=timestamp,
                cursor=cursor,
                limit=min(limit-len(messages),1000),
                include_all_metadata=False,
                inclusive=False
            )
            messages.extend(data.get('messages',[]))
            if data['response_metadata']:
                cursor = data['response_metadata'].get('next_cursor',None)
            else:
                break
        except SlackApiError as s:
            messages.append(f'Failed to fetch messages: {s}')
            return messages
    return messages

def get_messages(channel_id:str = None, days:int = 1) -> list[Any]:
    """Returns the list of latest messages from a given channel and the days requested"""
    messages = get_ch_messages(channel_id, days)
    thread_replies = []

    for message in messages:
        replies = [message]
        parts=[
            f'<@{get_user_name(m.get('user'))}> : {m.get('text','[No text]')}' for m in replies
        ]
        thread_replies.append('\n'.join(parts))
    
    return thread_replies

## TOOLS -----------------------------------------------------------------------

@mcp.tool()
def get_user_list() -> list[Any]:
    """Returns the user list from Slack workspace"""
    try:
        slack_client = Storage().slack_client
        data = slack_client.users_list()
    except SlackApiError as s:
        return [f'Users not found: error {s}']
    
    users = []
    for user in data['members']:
        id = user['id']
        user_name = get_user_name(id)
        users.append((user_name, id))
    return users

@mcp.tool()
def get_workspace_channels() -> list[Any]:
    """Returns a list of the channels inside a workspace, id, name and purpose of the channel"""
    try:
        slack_client = Storage().slack_client
        data = slack_client.conversations_list()
        ws_channels = []
        for channel in data['channels']:
            ch_id = channel['id']
            ch_name = channel['name']
            ch_purpose = channel['purpose']['value']
            ws_channels.append((ch_id,ch_name,ch_purpose))
        return ws_channels
    except SlackApiError as s:
        return [f'Error fetching ws channels: {s}']

@mcp.tool()
def get_user_channels(user_id:str = None) -> list[Any]:
    """Returns the channel list from a given user, specific channels present"""
    if not user_id:
        return ['No user provided']
    
    u_channels = []
    cursor = None

    while True:
        try:
            slack_client = Storage().slack_client
            data = slack_client.users_conversations(
                user=user_id,
                types='public_channel',
                cursor=cursor,
                limit=100
            )
            if 'channels' in data and isinstance(data['channels'],list):
                u_channels.extend(data['channels'] or [])
            if not cursor:
                break
        except SlackApiError as s:
            u_channels.append(f'Failed to fetch channels: {s}')
            return u_channels
    
    return [(channel['id'],channel['name']) for channel in u_channels]

@mcp.tool() ##TODO: Convert into a resource or prompt
def summarize_channel(channel_id:str = None, days:int = 1) -> str:
    """Given a channel ID and the days, summarizes the channel messages from the past days"""
    if not channel_id:
        return 'No Channel id provided'
    ch_messages = get_messages(channel_id=channel_id, days=days)
    prompt = f'summarize the following conversation from a channel in less than 6 bullet points: {ch_messages}.'
    llm_client = Storage().llm_client
    summary_text = llm_client.summarize(prompt)
    return summary_text

## -----------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport='stdio')

## Send messages chat.meMessage chat.postMessage, invite users into a channel conversations.invite, conversations.join join a ch conversations.leave, conversations.list
## to know all the space messages, conversations.members