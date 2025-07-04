from typing import Any
from modules.config import Settings
from modules.oci_client import Client
from modules.db import DataBase
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

mcp = FastMCP("W/L DB")

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
            self.db = DataBase(self.settings)
            self.llm_client = Client(self.settings)
            Storage._initialized = True
    
    def storage_data(self,data:str):
        self.merged_data = data
    
    def get_storage_data(self) -> str:
        return self.merged_data

def get_db_response(
        name_list,
        year=2010,
        type=None,
        region=None,
        customer=None,
        product=None
    ):
    db_query = Storage().db.build_query(name_list,year,type,region,customer,product)
    db_response = Storage().db.sort_files(db_query)
    lists = [list(group) for group in zip(*db_response)]
    return lists

def merge_md(file_list):
    info_pack = ''
    for data in file_list:
        info_pack = info_pack + '\n' + data
    return info_pack

def manage_filter(year,type,region,customer,product):
    data = get_db_response(['t.metadata.file_name','t.content'],year,type,region,customer,product)
    if not data:
        Storage().storage_data('Not data found')
        return ['No files found with that filter']
    else:
        merged_data = merge_md(data[1])
        Storage().storage_data(merged_data)
        return data[0]
    
def get_client_filter(prompt:str):
    r_dict = Storage().llm_client.filter_files(prompt)
    year_p = r_dict[0]
    type_p = r_dict[1]
    region_p = r_dict[2]
    customer_p = r_dict[3]
    product_p = r_dict[4]
    lists = manage_filter(year_p,type_p,region_p,customer_p,product_p)
    return lists

## TOOLS -----------------------------------------------------------------------

@mcp.tool()
def search_documetns_by_query(query:str = '') -> list[Any]:
    """Returns the available call report documents using the user query to build a DB request"""
    return get_client_filter(query)

@mcp.tool()
def get_available_filters() -> list[Any]:
    """Gives the user information about the filters that are available to search the call report documents"""
    responses = get_db_response(
        ['t.metadata.report_date','t.metadata.type','t.metadata.regions[0].region']
    )
    years = [int(date[:4]) for date in responses[0]]
    years.insert(0,2010)
    unique_years = sorted(set(years))

    responses[1].insert(0,"")
    unique_type = sorted(set(responses[1]))

    responses[2].insert(0,"")
    unique_region = sorted(set(responses[2]))

    filters = [unique_years,unique_type,unique_region]

    return filters

@mcp.tool()
def analyse_documents(query:str) -> str:
    """Based on the content of the call report documents filtered, answers the user query"""
    prompt = query + f' given the data in {Storage().get_storage_data()}'
    analysis = Storage().llm_client.provide_analysis(prompt)
    return analysis

## -----------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport='stdio')