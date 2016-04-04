
# coding: utf-8

# In[22]:

#Goal - Select all segments in a given lat/long bounds using the Strava API
#Problem - API only reuturns top 10 segments in bound
import stravalib
import pandas as pd
import numpy as np
import os
from sqlalchemy import create_engine
from polyline.codec import PolylineCodec
from datetime import datetime
import json


# In[2]:

engine = create_engine('postgresql+psycopg2://admin:password@localhost:5432/webdev6', 
                       convert_unicode=True)


# In[3]:

client = stravalib.client.Client(access_token=os.environ['STRAVA_APICODE'])
athlete = client.get_athlete()
print 'athlete name %s, athlete id %s.' %(athlete.firstname, athlete.id)


# In[16]:

def get_segs_from_api(client, extents, act_type):
    """Get segments for a client in extents [40.681, -89.636, 40.775, -89.504] 
    with act_type riding or running.
    Returns a dataframe of the segments with all details of the segments
    """
    segment_explorer = client.explore_segments(extents,
                                               activity_type=act_type)
    return segment_explorer

def seg_to_df(segment_explorer, act_type):
    dflist = []
    for seg in segment_explorer:
        print 'seg id %s, seg name %s, seg dist %s' %                (seg.id, seg.name, seg.distance)
        
        if act_type=='riding':
            acttype='ride'
        else:
            acttype='run'
            
        seg_detail = seg.segment
        newrow = {'seg_id' : int(seg.id),
                  'name' : str(seg.name),
                  'act_type' : str(acttype),
                  'elev_low' : 0, #float(seg_detail.elevation_low),
                  'elev_high' : 0, #float(seg_detail.elevation_high),
                  'start_lat' : float(seg.start_latlng[0]),
                  'start_long' : float(seg.start_latlng[1]),
                  'end_lat' : float(seg.end_latlng[0]),
                  'end_long' : float(seg.end_latlng[1]),
                  'date_created' : datetime.utcnow(), #seg_detail.created_at.replace(tzinfo=None),
                  'effort_cnt' : 0, #int(seg_detail.effort_count),
                  'ath_cnt' : 0, #int(seg_detail.athlete_count),
                  'cat' : int(seg.climb_category),
                  'elev_gain' : float(seg.elev_difference),
                  'distance' : float(seg.distance),
                  'seg_points' : str(seg.points),
                  'seg_points_decode' : PolylineCodec().decode(seg.points)
                 }
        dflist.append(newrow)
    
    seg_df = pd.DataFrame(dflist)
        
    return seg_df


# In[17]:

segment_explorer = get_segs_from_api(client, [40.8, -89.7, 40.9, -89.6], 'riding')
seg_df = seg_to_df(segment_explorer, 'riding')


# In[6]:

def create_points(lat_series, long_series):
    # Creates a string from a lat/long column to map to a Geography Point
    # datatype in PostGIS
    point_col = 'Point(' + str(long_series) + ' ' + str(lat_series) + ')'

    return point_col

seg_df['start_point'] = map(create_points, seg_df['start_lat'], seg_df['start_long'])
seg_df['end_point'] = map(create_points, seg_df['end_lat'], seg_df['end_long'])


# In[7]:

def get_acts_in_db(engine, table_name):
    # Return a list of already cached segments in the database
    already_dl_seg_id_list = []
    try:
        args = 'SELECT seg_id from "%s"' % (table_name)
        df = pd.read_sql(args, engine)
        already_dl_seg_id_list = df['seg_id']
    except:
        print "no activities in database!  downloading all segments in range..."

    return already_dl_seg_id_list


def clean_cached_segs(dl_lst, new_seg_df):
    # Remove segments already in database from the dataframe
    new_seg_df['rows_to_drop'] = new_seg_df['seg_id'].isin(dl_lst)
    new_seg_df.drop(new_seg_df[new_seg_df.rows_to_drop==True].index, inplace=True)
    return new_seg_df


# In[8]:

dl_lst = get_acts_in_db(engine, 'Segment')
seg_df = clean_cached_segs(dl_lst, seg_df)


# In[18]:

seg_df.head(2)


# In[51]:

#Converts a dataframe to a geojson Point output
def df_to_geojson_point(df, properties, lat='latitude', lon='longitude'):
    geojson = {'type':'FeatureCollection', 'features':[]}
    for _, row in df.iterrows():
        feature = {'type':'Feature',
                   'properties':{},
                   'geometry':{'type':'Point',
                               'coordinates':[]}}
        feature['geometry']['coordinates'] = [row[lon],row[lat]]
        for prop in properties:
            feature['properties'][prop] = row[prop]
        geojson['features'].append(feature)
    return geojson

#Converts a dataframe to a geojson LineString output
def df_to_geojson_line(df, properties, coords):
    geojson = {'type':'FeatureCollection', 'features':[]}
    for _, row in df.iterrows():
        feature = {'type':'Feature',
                   'properties':{},
                   'geometry':{'type':'LineString',
                               'coordinates': ''}}
        feature['geometry']['coordinates'] = row[coords]
        for prop in properties:
            feature['properties'][prop] = row[prop]
        geojson['features'].append(feature)
    return geojson


# In[52]:

geojson = df_to_geojson_line(seg_df, ['name', 'act_type', 'distance', 'elev_gain'], 'seg_points_decode')


# In[53]:

output_filename = 'dataset.js'
with open(output_filename, 'wb') as output_file:
    output_file.write('var dataset = ')
    json.dump(geojson, output_file, indent=2) 


# In[10]:

seg_df.set_index('seg_id', inplace=True)
seg_df.drop(['start_lat','start_long','end_lat','end_long', 'rows_to_drop'], axis=1, inplace=True)
seg_df.to_sql('Segment', engine, if_exists='append', index=True, index_label='seg_id')


# In[34]:

from IPython.display import Javascript


# In[40]:

from IPython.display import Javascript
#Create a javascript variable with our geojson data to visualize in the browser
#The data object 'vizObj' will be a global varialbe in our window that 
#We can pass to another javascript function call
Javascript("""window.vizObj={};""".format(geojson))


# In[42]:

get_ipython().run_cell_magic(u'javascript', u'', u'//Testing that the window.vizObj variable is accessable\nconsole.log(window.vizObj);')


# In[43]:

#Now let's make some HTML to style our intended mapbox output
from IPython.display import HTML
HTML("""
<style> #map {
  position: relative;
  width: auto;
  height: 650px;
  overflow:visible;
}
</style>
""")


# In[44]:

get_ipython().run_cell_magic(u'javascript', u'', u"//Load required javascript libraries\nrequire.config({\n  paths: {\n      mapboxgl: 'https://api.tiles.mapbox.com/mapbox-gl-js/v0.16.0/mapbox-gl',\n      bootstrap: 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min'\n  }\n});")


# In[56]:

get_ipython().run_cell_magic(u'javascript', u'', u'IPython.OutputArea.auto_scroll_threshold = 9999;\nrequire([\'mapboxgl\', \'bootstrap\'], function(mapboxgl, bootstrap){\n    mapboxgl.accessToken = \'pk.eyJ1IjoicnNiYXVtYW5uIiwiYSI6IjdiOWEzZGIyMGNkOGY3NWQ4ZTBhN2Y5ZGU2Mzg2NDY2In0.jycgv7qwF8MMIWt4cT0RaQ\';\n    var map = new mapboxgl.Map({\n        container: \'map\', // container id\n        style: \'mapbox://styles/mapbox/dark-v8\', //stylesheet location\n        center: [-89.948470, 40.783860], // starting position\n        zoom: 10 // starting zoom \n    });\n    \n    \n    function addSegLayer(mapid) {\n        // Mapbox GL JS Api - import segment\n        var segment_src = new mapboxgl.GeoJSONSource({\n            data: window.vizObj,\n            maxzoom: 18,\n            buffer: 1,\n            tolerance: 1\n        });\n        try {\n            mapid.addSource(\'segment\', segment_src);\n            mapid.addLayer({\n                id: \'segment\',\n                type: \'line\',\n                source: \'segment\',\n                paint: {\n                    "line-opacity": 1,\n                    "line-width": 5,\n                    "line-color": \'red\',\n                }\n            });\n        } catch (err) {\n            console.log(err);\n        }\n    };\n    \n    map.once(\'style.load\', function(e) {\n        addSegLayer(map);\n        map.addControl(new mapboxgl.Navigation({\n            position: \'top-left\'\n        }));\n    });\n    \n});\nelement.append("<div id=\'map\'></div>");')


# In[ ]:



