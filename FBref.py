#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
import bs4 as bs
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.offsetbox import TextArea, DrawingArea, OffsetImage, AnnotationBbox
from matplotlib.patches import Arc, Rectangle, ConnectionPatch
from matplotlib.pyplot import figure
import matplotlib.image as mpimg
from matplotlib.path import Path
from matplotlib.spines import Spine
from matplotlib.projections.polar import PolarAxes
from matplotlib.projections import register_projection
from pandas.io.json import json_normalize
from sklearn.metrics.pairwise import cosine_similarity
import re
import json
import ast
import time




def radar_factory(num_vars, frame='circle'):
    """Create a radar chart with `num_vars` axes.

    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    frame : {'circle' | 'polygon'}
        Shape of frame surrounding axes.

    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)

    def draw_poly_patch(self):
        # rotate theta such that the first axis is at the top
        verts = unit_poly_verts(theta + np.pi / 2)
        return plt.Polygon(verts, closed=True, edgecolor='k')

    def draw_circle_patch(self):
        # unit circle centered on (0.5, 0.5)
        return plt.Circle((0.5, 0.5), 10)

    patch_dict = {'polygon': draw_poly_patch, 'circle': draw_circle_patch}
    if frame not in patch_dict:
        raise ValueError('unknown value for `frame`: %s' % frame)

    class RadarAxes(PolarAxes):

        name = 'radar'
        # use 1 line segment to connect specified points
        RESOLUTION = 2
        # define draw_frame method
        draw_patch = patch_dict[frame]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location('N')

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            # FIXME: markers at x[0], y[0] get doubled-up
            if x[0] != x[-1]:
                x = np.concatenate((x, [x[0]]))
                y = np.concatenate((y, [y[0]]))
                line.set_data(x, y)

        def set_varlabels(self, labels, **kwargs):
            
            self.set_thetagrids(np.degrees(theta), labels, **kwargs)

        def _gen_axes_patch(self):
            return self.draw_patch()

        def _gen_axes_spines(self):
            if frame == 'circle':
                return super()._gen_axes_spines()
            # The following is a hack to get the spines (i.e. the axes frame)
            # to draw correctly for a polygon frame.

            # spine_type must be 'left', 'right', 'top', 'bottom', or `circle`.
            spine_type = 'circle'
            verts = unit_poly_verts(theta + np.pi / 2)
            # close off polygon by repeating first vertex
            verts.append(verts[0])
            path = Path(verts)

            spine = Spine(self, spine_type, path)
            spine.set_transform(self.transAxes)
            return {'polar': spine}

    register_projection(RadarAxes)
    return theta


def unit_poly_verts(theta):
    """Return vertices of polygon for subplot axes.

    This polygon is circumscribed by a unit circle centered at (0.5, 0.5)
    """
    x0, y0, r = [0.5] * 3
    verts = [(r*np.cos(t) + x0, r*np.sin(t) + y0) for t in theta]
    return verts


# In[3]:


'''
instantiate chrome web drive and specify the direction where 
the files will be downloaded in download default directory parameter. 

league_dict is a dictionary that contains each league that 
we want to scrap as key and its id in fbref as the value. 
This helps us to scrap the url of each league.

titles is a list of the title of the tables that we are
scraping for each team. This helps us in naming the directories
when the data is being scraped
'''


chrome_options = webdriver.ChromeOptions()
profile = {"download.default_directory": "C:\\Users\\Yassine\\defenders_data",
           "download.prompt_for_download": False,
           "download.directory_upgrade": True,
          }
chrome_options.add_experimental_option("prefs", profile)

url  = "https://www.fbref.com/"

leagues_dict = {'Serie_A': '11', 'SuperLiga': '32', 'MLS': '22', 'Eridivisie': '23', 'Ligue_1': '13', 'Premier_League': '9', 'La_Liga': '12'
                ,'Bundesliga':'20'}

titles = ["standard_stats", "shooting", "passing", "pass_types", "goal_shot_creation", "defensive_action", "possesion", 
          "playing_time", "misc_stats", "player_summary", "gk_summary"] 

file_name = "sportsref_download.csv"
defender_template_files = ["passing", "defensive_action", "misc_stats"] 




'''
get all the teams and their respective links in FBref by scraping javascript from the website
it returns a dictionary containg each league id in keys and a list of dictionaries (link in key, team name in value) 
of the league teams in values
'''

def get_leagues_teams():
    
    driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
    driver.get(url)
    soup = BeautifulSoup(driver.page_source,"html.parser")
    scripts = soup.find_all('script')
    for script in scripts:
        if "sr_goto_json" in script.get_text():
            teams_urls = script.get_text()
            break
    t = teams_urls.replace("\n","").split("=")[5:][0][:-1].replace(", }", "}")
    leagues = eval(t.replace(" ",""))
    leagues_keys = list(leagues.keys())
    leagues_teams = list(leagues.values())
    for league in leagues_keys:
        teams = leagues[league][1:]
        leagues[league] = teams
    driver.close()
    return leagues




'''
this function gets the statistics tables mentioned in titles. The league name is passed as an argument . 
The statistics are got for each team in that specific league.
'''
def get_league_stats(league_name):
    
    leagues = get_leagues_teams() 
    if league_name in list(leagues_dict.keys()):
            for team in leagues[leagues_dict[league_name]]:
                    indices = []
                    profile = {"download.default_directory": "C:\\Users\\Yassine\\defenders_data",
                                "download.prompt_for_download": False,
                                "download.directory_upgrade": True,
                                  }
                    chrome_options.add_experimental_option("prefs", profile)
                    driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                    driver.get(url + list(team.keys())[0])
                    elements = driver.find_elements_by_tag_name('button')
                    for element in elements: 
                        if "comma" in str(element.get_attribute("tip")):
                            indices.append(elements.index(element))
                    driver.close()
                    del indices[1:4]
                    print(len(indices))
                    for x in range(0,len(titles)):                            
                        try:
                            profile = {"download.default_directory": "C:\\Users\\Yassine\\defenders_data\\" + str(league_name) + "\\" + str(list(team.values())[0]) + "\\" + titles[x],
                               "download.prompt_for_download": False,
                               "download.directory_upgrade": True, }
                            
                            chrome_options.add_experimental_option("prefs", profile)
                            driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                            driver.get(url + list(team.keys())[0])
                            elements = driver.find_elements_by_tag_name('button')[indices[x]]
                            driver.execute_script("arguments[0].click();", elements)
                            time.sleep(5)
                            driver.close()
                        except:
                            print("Something wrong Happened" + str(list(team.values())[0]))
                    
        




'''
This function takes as an argument a league name and returns a list of the links of all the games that have been played 
in that league
'''
def get_fixtures_links(league_name):  
    link = league_name + " Fixtures"
    fixtures_links = []
    profile = {"download.default_directory": "C:\\Users\\Yassine",
                                "download.prompt_for_download": False,
                                "download.directory_upgrade": True,
                                  }
    chrome_options.add_experimental_option("prefs", profile)
    driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
    driver.get(url+'\\' + 'en' + '\\' + 'comps' + '\\' +leagues_dict[league_name] + '\\' + 'schedule' + '\\'+ link.replace(" ", "-") )
    elements = driver.find_elements_by_tag_name('a')
    for element in elements: 
        if "matches" in str(element.get_attribute("href")) and "Premier" in str(element.get_attribute("href")).split("-") and str(element.get_attribute("href")) not in fixtures_links:
            fixtures_links.append(str(element.get_attribute("href")))
    driver.close()
    return fixtures_links   
    






'''
This code is for scrapping the data of all the fixtures in the PL.
'''


sections  = ['summary','passing','passing_types','defense','possession','misc']
for fixture in range(0,len(fixtures_links)):
    profile = {"download.default_directory": "C:\\Users\\Yassine\\",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "profile.default_content_setting_values.automatic_downloads": 1}
    chrome_options.add_experimental_option("prefs", profile)
    driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
    driver.get(fixtures_links[fixture])
    tabs = driver.find_elements_by_xpath('//div[contains(@id,  "stats")]')
    ids = []
    for tab in tabs:
        if "summary" in tab.get_attribute('id'):
            if tab.get_attribute('id').split("_")[2] not in ids:
                ids.append(tab.get_attribute('id').split("_")[2])
    driver.close()
    try: 
        for i in range(0,17):
            if i in range(0,6):
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + ids[0] + "\\" + sections[i],
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])
                id = "all_stats_" + ids[0] + "_" + sections[i]
                button = "#all_stats_" + ids[0] + "_" + sections[i]
                table_button = driver.find_element_by_xpath("//div[@id = '" + id + "']//button[@data-show = '" + button + "' ]")
                driver.execute_script("arguments[0].click();",table_button)
                time.sleep(2)
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)                                                                                       
            if i == 6:
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + ids[0] + "\\" + "keeper",
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])                                                                                                  
                id = "all_keeper_stats_" + ids[0]
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)
            if i in range(7,13):
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + ids[1] + "\\" + sections[i-7],
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])                                                                                                
                id = "all_stats_" + ids[1] + "_" + sections[i-7]
                button = "#all_stats_" + ids[1] + "_" + sections[i-7]
                table_button = driver.find_element_by_xpath("//div[@id = '" + id + "']//button[@data-show = '" + button + "' ]")
                driver.execute_script("arguments[0].click();",table_button)
                time.sleep(2)
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)
            if i == 13:
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + ids[1] + "\\" + "keeper",
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])  
                id = "all_keeper_stats_" + ids[1]
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)
            if i == 14:
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + "all_shots",
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])  
                id = "all_shots_all"
                button = "#all_shots_all" 
                table_button = driver.find_element_by_xpath("//div[@id = '" + id + "']//button[@data-show = '" + button + "' ]")
                driver.execute_script("arguments[0].click();",table_button)
                time.sleep(2)
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)
            if i == 15:
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + ids[0] + "\\" + "shots",
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])  
                id = "all_shots_" + ids[0]
                button = "#all_shots_" + ids[0] 
                table_button = driver.find_element_by_xpath("//div[@id = '" + id + "']//button[@data-show = '" + button + "' ]")
                driver.execute_script("arguments[0].click();",table_button)
                time.sleep(2)
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)
            if i == 16:
                profile = {"download.default_directory": "C:\\Users\\Yassine\\fixtures_data\\" + fixtures_links[fixture].split("/")[-1] + "\\" + ids[1] + "\\" + "shots",
                           "download.prompt_for_download": False,
                           "download.directory_upgrade": True,
                           "profile.default_content_setting_values.automatic_downloads": 1}
                chrome_options.add_experimental_option("prefs", profile)
                driver=webdriver.Chrome(options=chrome_options, executable_path=r'C:\Users\Yassine\Downloads\chromedriver_win32\chromedriver.exe')
                driver.get(fixtures_links[fixture])                                                                                                  
                id = "all_shots_" + ids[1]
                button = "#all_shots_" + ids[1] 
                table_button = driver.find_element_by_xpath("//div[@id = '" + id + "']//button[@data-show = '" + button + "' ]")
                driver.execute_script("arguments[0].click();",table_button)
                time.sleep(2)
                download_button = driver.find_element_by_xpath('//div[@id = "' + id + '"]//div[@class ="section_heading"]//li[@class="hasmore"]//button[contains(@tip, "comma")]')
                driver.execute_script("arguments[0].click();",download_button)
                time.sleep(2)
            driver.close()
    except:
        print("Something Wrong Happened" + fixtures_links[fixture] + " " + str(fixture))
     





def refine_passing_df(df):
    x = list(df.columns)
    y = list(df.iloc[0])
    for e in range(0,len(y)):
        x[e] = y[e]
        if e in  range(5,10):
            x[e] = "Total_" + x[e]
        if e in  range(10,13):
            x[e] = "Short_" + x[e]
        if e in  range(13,16):
            x[e] = "Medium_" + x[e]
        if e in  range(16,19):
            x[e] = "Long_" + x[e]
        if "3" in x[e]:
            x[e] = "1/3"
    df.columns = tuple(x)
    df = df.drop(columns=['Matches'])
    return df[1:]





def refine_misc_df(df):
    x = list(df.columns)
    y = list(df.iloc[0])
    for e in range(0,len(y)):
        x[e] = y[e]
        if e in  range(5,18):
            x[e] = "Performance_" + x[e]
        if e in  range(18,21):
            x[e] = "Aerial_Duels_" + x[e]
    df.columns = tuple(x)
    df = df.drop(columns=['Matches'])
    return df[1:]


def refine_da_df(df):
    x = list(df.columns)
    y = list(df.iloc[0])
    for e in range(0,len(y)):
        x[e] = y[e]
        if e in  range(5,10):
            x[e] = "Tackles_" + x[e]
        if e in  range(10,14):
            x[e] = "Vs_Dribbles_" + x[e]
        if e in  range(14,20):
            x[e] = "Pressures_" + x[e]
        if e in  range(20,24):
            x[e] = "Blocks_" + x[e]
    df.columns = tuple(x)
    df = df.drop(columns=['Matches'])
    return df[1:]



def get_defensive_data():
    passing_frames = []
    da_frames = []
    misc_frames = []
    for league_name in list(leagues_dict.keys()):
        if league_name not in ["SuperLiga", "Eridivisie", "MLS"]:
                for team in leagues[leagues_dict[league_name]]:
                   for x in defender_template_files:                            
                        team_name = list(team.values())[0]
                        if x =="passing":
                            df_passing = refine_passing_df(pd.read_csv('.\defenders_data\\' +str(league_name) +'\\'+str(team_name)+'\\' +x + '\\' +file_name, 
                                                              encoding="utf-8"))
                            df_passing["Team"] = team_name
                            passing_frames.append(df_passing)
                        if x == "defensive_action":
                            df_da = refine_da_df(pd.read_csv('.\defenders_data\\' +str(league_name) +'\\'+str(team_name)+'\\' +x + '\\' +file_name, 
                                                              encoding="utf-8"))
                            df_da["Team"] = team_name
                            da_frames.append(df_da)
                        if x == "misc_stats":
                            df_misc = refine_misc_df(pd.read_csv('.\defenders_data\\' +str(league_name) +'\\'+str(team_name)+'\\' +x + '\\' +file_name, 
                                                              encoding="utf-8"))
                            df_misc["Team"] = team_name 
                            misc_frames.append(df_misc)
    passing_df = pd.concat(passing_frames)
    da_df = pd.concat(da_frames)
    misc_df = pd.concat(misc_frames)
    return passing_df, da_df, misc_df    



passing_df, da_df, misc_df = get_defensive_data()



passing_df = passing_df[passing_df.Pos.str.contains('DF',case=False, na=False)][['Player', 'Pos','Age', '90s', 'Total_Cmp',
                                                                                  'Total_Cmp%', 'Total_PrgDist','Long_Cmp', 
                                                                                  'Long_Cmp%', 'Ast', 'xA', '1/3',
                                                                                  'PPA', 'CrsPA', 'Prog', 'Team']]
misc_df = misc_df[misc_df.Pos.str.contains('DF',case=False, na=False)][['Player', 'Pos','Age', '90s', 'Performance_Fls', 
                                                                        'Performance_Recov', 'Aerial_Duels_Won', 'Aerial_Duels_Lost',
                                                                        'Aerial_Duels_Won%', 'Team']]
da_df = da_df[da_df.Pos.str.contains('DF',case=False, na=False)][['Player', 'Pos', 'Age', '90s', 'Tackles_Tkl', 'Tackles_TklW',
                                                                   'Vs_Dribbles_Tkl' ,'Vs_Dribbles_Tkl%','Vs_Dribbles_Past', 
                                                                   'Pressures_Press', 'Pressures_Succ', 'Pressures_%',
                                                                   'Blocks_Blocks', 'Int', 'Clr', 'Err', 'Team']]




#merging the dataframes of defenders
new_df = pd.merge(pd.merge(misc_df, da_df, on=['Player','Age', 'Pos', '90s', 'Team']), passing_df, on=['Player','Age', 'Pos', '90s', 'Team']) 
#new_df = pd.merge(new_df, passing_df, on=['Player','Age', 'Pos', '90s', 'Team'])

#converting the columns to floats in order to be able to see the mean and counts etc
for column in list(new_df.columns):
    if column not in ["Player", 'Pos', 'Team']:
        new_df[column] = new_df[column].astype(float)
        
#selecting only defenders who played more than 5 games and removing a player with incomplete data      
final_df = new_df[(new_df['90s'] >= 5) & (new_df['Player'] != "Nicholas Opoku")]
final_df





#calculate metrics per 90 
per_90_df = final_df
for column in list(final_df.columns):
    if column not in ["Player", 'Age','Pos', 'Team', '90s'] and "%" not in column:
        column_list = list(final_df[column])
        for x in range(0,len(column_list)):
            column_list[x] = round(column_list[x]/list(final_df['90s'])[x],2)
        per_90_df[column] = column_list
per_90_df




#calculating the z score for each data point in each column ( (value - column average)/column std)
z_score_df = per_90_df
for column in list(z_score_df.columns):
    if column not in ["Player", 'Age','Pos', 'Team', '90s']:
        column_list = list(per_90_df[column])
        for x in range(0,len(column_list)):
            if column_list[x] in ['Performance_Fls', 'Performance_Recov','Aerial_Duels_Won', 
                                     'Aerial_Duels_Lost', 'Aerial_Duels_Won%','Tackles_Tkl', 
                                     'Tackles_TklW', 'Vs_Dribbles_Tkl', 'Vs_Dribbles_Tkl%',
                                     'Vs_Dribbles_Past', 'Pressures_Press', 'Pressures_Succ', 
                                     'Pressures_%','Blocks_Blocks', 'Int', 'Clr', 'Err']:
                    column_list[x] = round(2*(column_list[x] - per_90_df[column].mean())/per_90_df[column].std(),2)
            else:
                    column_list[x] = round((column_list[x] - per_90_df[column].mean())/per_90_df[column].std(),2)
        
        z_score_df[column] = column_list
cols = list(z_score_df.columns)
cols[4] = "Team"
cols[9] = "Performance_Fls"
z_score_df = z_score_df[cols]
z_score_df



'''
function to get 3 similar players based on cosin similarity. Takes player names as an argument
and returns a list of the 3 highest cos similarity coefficients and a dataframe of those players.
'''

def get_similar_players(player_name):
    player_index = [list(z_score_df["Player"]).index(x) for x in list(z_score_df["Player"]) if player_name  in x]
    player_index = int(player_index[0])
    #print(player_index)
    df1 = z_score_df.iloc[:,5:] 
    cos = cosine_similarity(df1, df1)
    player_cos = sorted(list(cos[player_index]))[-4:-1]
    indexes = [list(cos[player_index]).index(x) for x in player_cos ]
    indexes.append(player_index)
    return player_cos , z_score_df.iloc[indexes]





player_cos, x = get_similar_players("Ramos")
player_cos.append('')
players_data = [x.iloc[:,5:].iloc[i,:].values for i in range(4)]
data = [list(x.iloc[:,5:]),players_data]
N = len(data[0])
theta = radar_factory(N, frame='polygon')
#data = example_data()
spoke_labels = data.pop(0)

    
fig, ax = plt.subplots(figsize=(30, 15), subplot_kw=dict(projection='radar'))
fig.subplots_adjust(wspace=0.25, hspace=0.20, top=0.85, bottom=0.05)
colors = ['b', 'g', 'y', 'r']
# Plot the four cases from the example data on separate axes
#for (title, case_data) in data:
    #ax.set_title(title, weight='bold', size='medium', position=(0.5, 1.1),
                     #horizontalalignment='center', verticalalignment='center')
case_data = data[0]
for d, color in zip(case_data, colors):
    ax.plot(theta, d, color=color, label='_nolegend_')
    ax.fill(theta, d, facecolor=color, alpha=0.25)
    subplot_kw=dict(size=14, weight='bold')
    ax.set_varlabels(spoke_labels, **subplot_kw )

# add legend relative to top-left plot
#ax = axes[0, 0]
labels = [list(x["Player"].values)[i] + ", " + list(x["Team"].values)[i] + ", (similarity degree " + str(round(player_cos[i]*100,2)) + " %)" for i in range (0,len(player_cos)-1)]
labels.append(list(x["Player"].values)[-1] + ", " + list(x["Team"].values)[-1])
labels = tuple(labels)
#ax = fig.add_axes([0.8, 0.1, 0.6, 0.75])
legend = ax.legend(labels, loc=(1., .95),
                       fontsize='x-large')
fig.text(0.5, 0.89, 'Similar Players to ' + list(x["Player"].values)[-1] + ' '  + '(' + list(x["Team"].values)[-1] + ')' ,
             horizontalalignment='center', color='black', weight='heavy', style =
         'italic',
            fontsize=25)
fig.text(0.52, 0.1, 'Hamza Jebbar' ,
             horizontalalignment='center', color='red', weight='bold',
            fontsize=25)
ax.spines['polar'].set_visible(False)
#ax.set_facecolor((0.39, 0.58, 0.84))
plt.savefig(fname = './radars/' + list(x["Player"].values)[-1], dpi=None, facecolor='w', edgecolor='w',
        orientation='landscape', papertype='a1', format=None)



plt.show()



def get_columns_name():
    header = []
    columns_name = soup.find('thead')
    for row in columns_name.find_all('th'):
        name = row.get_text(strip=True, separator = "##")
        header.append(name)
    header = header[7:len(header)-1]
    return header
    


# In[ ]:


def get_data():
    numbers = []
    data = soup.find('tbody')
    rows = data.find_all('tr')
    for row in rows:
        cell= row.find_all("th")
        numbers.append(cell[0].get_text(strip = True))
        cell= row.find_all("td")
        for i in range(len(cell)):
            if (cell[i].get_text(strip = True) == "Matches"): 
                pass
            else:
                numbers.append(cell[i].get_text(strip = True))
    return numbers


# In[ ]:


def fill_blank(data_array):
    #result = filter(lambda x: x != "", data_array) 
    #result = map(lambda x: x if (x!="") else "Nan",data_array) 
    #return result
    for n, i in enumerate(data_array):
      if i == "":
        data_array[n] = "NaN"
    return data_array
z= fill_blank(get_data())
z

#get_data()[20] == "NaN"


# In[ ]:


def fill_dataframe(data, columns):
    ar =[]
    data_length = len(data)
    columns_length = len(columns)
    rows = int(data_length/columns_length)
    for i in range(0,rows):
        j = i*columns_length
        k = (i+1)*columns_length
        ar.append(data[j:k])
    df = pd.DataFrame(ar, columns=columns)
    return df
fill_dataframe(fill_blank(get_data()),columns = get_columns_name())

