
import pandas as pd
import numpy as np
import ezdxf
from pathlib import Path
import math
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import json
import os,sys
from django.conf import settings
import django
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SKM.settings')
data_folder = settings.BASE_DIR / 'dummy' / 'SMH_PROTOTYPE_FILE/'
django.setup()


# Parse the JSON data passed as a command-line argument
if len(sys.argv) > 1:
    input_data = json.loads(sys.argv[1])
    
    # Now you can access the data like this:
    project_name = input_data.get('project_name', '')
    u_W = input_data.get('width', 0)
    u_L = input_data.get('length', 0)
    u_Bedroom = input_data.get('bedroom', 0)
    u_Bathroom = input_data.get('bathroom', 0)
    u_Car = input_data.get('car', 0)
    u_Temple = input_data.get('temple', 0)
    u_Garden = input_data.get('garden', 0)
    u_Living_Room = input_data.get('living_room', 0)
    u_Store_Room = input_data.get('store_room', 0)
    u_Plot_Size = u_W*u_L
    u_Aspect_Ratio = u_W/u_W

    # Use these variables instead of input() calls
else:
    print("No input data provided")
    sys.exit(1)


new_point = pd.DataFrame({'Total Area':[u_Plot_Size], 'Total Area width':[u_W],'Total Area length':[u_L],'No_of_Bedrooms':[u_Bedroom],'No_of_Bathrooms':[u_Bathroom],
                   'No_of_Parking':[u_Car],'No_of_Poojarooms':[u_Temple] , 'No_of_Garden':[u_Garden] ,'No_of_Livingrooms':[u_Living_Room],'No_of_Storerooms':[u_Store_Room] })
User_LB = [u_W,u_L]



pd.options.mode.copy_on_write = True 

def meta_data_creator(sample):
   
    meta_data = []

    for layer_name in sample.Layer.unique():

        space = sample[sample['Layer'] == layer_name]

        space['x_diff'] = space['X_end'] - space['X_start']
        space['y_diff'] = space['Y_end'] - space['Y_start']

        space['x_distance'] = np.abs(space['x_diff'])
        space['y_distance'] = np.abs(space['y_diff'])

        length = max(space['x_distance'])/12
        width = max(space['y_distance'])/12

        meta_data.append({
                'Layer': layer_name,
                'length': length,
                'width': width
            })

    layer_info = pd.DataFrame(meta_data) 
    
    
    layer_info.loc[layer_info['Layer'] == 'Boundary', 'Layer'] = 'Total Area'
    layer_info.loc[layer_info['Layer'] == 'BoundaryWalls', 'Layer'] = 'Total Area'
    layer_info.loc[layer_info['Layer'] == 'Pooja', 'Layer'] = 'Temple'
    layer_info = layer_info[~(layer_info['Layer'] == '0')]
    #layer_info = layer_info[~(layer_info['Layer'] == 'Garden')]

    
    return layer_info


def metadata_vectorizer(layer_info, sample, file_name):
   
    df_area = pd.DataFrame(columns = layer_info.Layer.to_list())
    df_area.reindex([file_name])
    Area = layer_info['length'] * layer_info['width']
    Area = Area.to_list()
    df_area.loc[file_name] = Area
    
    #df_area['Carpet Area'] = carpet_area(layer_info)
    #df_area['Slab Area'] = slab_area(layer_info)
    
    
    length_column = (layer_info['Layer'] + ' length').to_list()
    df_length = pd.DataFrame(columns = length_column)         
    df_length.reindex([file_name])
    df_length.loc[file_name] = layer_info['length'].to_list()
    

    
    width_column = (layer_info['Layer'] + ' width').to_list()
    df_width = pd.DataFrame(columns = width_column)
    df_width.reindex([file_name])
    df_width.loc[file_name] = layer_info['width'].to_list()
    
    
    room_no_cols = ['No_of_Bedrooms', 'No_of_Bathrooms', 'No_of_Livingrooms', 'No_of_Kitchens', 'No_of_Dinings',
                   'No_of_Kitchen&Dining', 'No_of_Storerooms', 'No_of_Garden', 'No_of_Parking','No_of_Poojarooms','No_of_WashArea']
    df_room = pd.DataFrame(columns = room_no_cols)
    df_room.reindex([file_name])
    
    lst = ['BedRoom','BathRoom','LivingRoom','Kitchen','DiningRoom',
          'Kitchen & Dining','StoreRoom',r'\bGarden\b','Parking','PoojaRoom','WashArea']
    
    count = []
    for i in lst:
        val = sample[sample['Type'] == 'MTEXT']['Layer'].str.count(i).sum()
        count.append(val)
    
    df_room.loc[file_name] = count
    
    
    
    df_concatenated = pd.concat([df_area, df_length, df_width, df_room],  axis=1)
    
    return df_concatenated 


def calculate_length(start, end):
    return math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2 + (end.z - start.z)**2)

#DXF to PANDAS DATAFRAME
def Dxf_to_DF(filename):
    doc = ezdxf.readfile(filename)
    msp = doc.modelspace()
    
    entities_data = []
    for entity in msp:
        entity_data = {'Type': entity.dxftype(), 'Layer': entity.dxf.layer}
        if entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            length = calculate_length(start, end)
            entity_data.update({
                'X_start': start.x, 'Y_start': start.y, 'Z_start': start.z,
                'X_end': end.x, 'Y_end': end.y, 'Z_end': end.z,
                'Length': length})
            horizontal = abs(end.x - start.x) > abs(end.y - start.y)
            vertical = not horizontal
            entity_data.update({'Horizontal': horizontal, 'Vertical': vertical})
            
            
        elif entity.dxftype() == 'CIRCLE':
            center = entity.dxf.center
            radius = entity.dxf.radius
            entity_data.update({
                'X_center': center.x, 'Y_center': center.y, 'Z_center': center.z,
                'Radius': radius})
            
        elif entity.dxftype() == 'ARC':
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = entity.dxf.start_angle
            end_angle = entity.dxf.end_angle
            entity_data.update({
                'X_center': center.x, 'Y_center': center.y, 'Z_center': center.z,
                'Radius': radius,
                'Start Angle': start_angle,
                'End Angle': end_angle})
            
        elif entity.dxftype() == 'TEXT':
            insert = entity.dxf.insert
            text = entity.dxf.text
            entity_data.update({
                'X_insert': insert.x, 'Y_insert': insert.y, 'Z_insert': insert.z,
                'Text': text})
        elif entity.dxftype() == 'MTEXT':
            text = entity.plain_text()
            insertion_point = entity.dxf.insert
            entity_data.update({
                'Text': text,
                'X_insert': insertion_point.x,
                'Y_insert': insertion_point.y,
                'Z_insert': insertion_point.z
            })
            
            
        entities_data.append(entity_data)
    
    return pd.DataFrame(entities_data)

def meta_main(dxf_file):
    
    file = ezdxf.readfile(dxf_file)
    
#     adjust_dxf_coordinates_to00(dxf_file)
    sample = Dxf_to_DF(dxf_file)
    
    layer_info = meta_data_creator(sample)
    meta = metadata_vectorizer(layer_info, sample, file.filename) ## file name in dxf_file
    
    return meta

def Data_creation(file_name_list):
    Meta_data = pd.DataFrame(columns = ['Total Area'])
    for i in file_name_list:
        Meta_data = pd.concat([Meta_data,meta_main(i)])
    return Meta_data





def Similarity_fuc(new_point, MetaData):
    cols = new_point.columns
    MetaData = MetaData[cols]
    # Separate categorical and continuous data
    data_cat = MetaData.select_dtypes(include='object')
    data_cont = MetaData.select_dtypes(exclude='object')

    new_data_cat = new_point.select_dtypes(include='object')
    new_data_cont = new_point.select_dtypes(exclude='object')
    
    # Standardize continuous data
    scaler = StandardScaler()
    data_cont_S = scaler.fit_transform(data_cont)
    new_data_cont_S = scaler.transform(new_data_cont)
    
    data_cont_S_DF = pd.DataFrame(data_cont_S, 
                                  columns = data_cont.columns + '_S', 
                                  index = data_cont.index)
    new_data_cont_S_DF = pd.DataFrame(new_data_cont_S, 
                                      columns = new_data_cont.columns + '_S', 
                                      index = new_data_cont.index)
    
    
    
    # Combine continuous and categorical data
    data_comb = pd.concat([data_cont_S_DF, data_cat], axis=1)
    new_data_comb = pd.concat([new_data_cont_S_DF, new_data_cat], axis=1)
    
    # Ensure the weights match the number of features in the combined data
    num_features = data_comb.shape[1]
    weights = np.ones(num_features)
    weights /= weights.sum()

    # Manually compute the weighted distances
    new_data_point = new_data_comb.values.flatten()
    weighted_distances = np.sqrt(np.sum(weights * ((data_comb.values - new_data_point) ** 2), axis=1))

    # Find the indices of the k-nearest neighbors (k=3)
    k = 3
    nearest_neighbors_indices = np.argsort(weighted_distances)[:k]

    # Get the nearest neighbors
    nearest_neighbors = MetaData.iloc[nearest_neighbors_indices]
    
    # Calculate differences
    differences = []
    for idx in nearest_neighbors_indices:
        neighbor = MetaData.iloc[idx]
        diff = {}
        for col in MetaData.columns:
            if MetaData[col].dtype == 'object':
                diff[col] = neighbor[col] == new_point[col].values[0]
            else:
                diff[col] = neighbor[col] - new_point[col].values[0]
        differences.append(diff)
    
    Differences = pd.DataFrame(differences, index=nearest_neighbors.index)
    
    return nearest_neighbors, Differences



def plot_dxf(filename):
    doc = ezdxf.readfile(filename)
    msp = doc.modelspace()
    fig, ax = plt.subplots(figsize=(12, 9))
    for entity in msp:
        if entity.dxftype() == 'LINE':
            start = (entity.dxf.start.x / 12, entity.dxf.start.y / 12)  # Convert inches to feet
            end = (entity.dxf.end.x / 12, entity.dxf.end.y / 12)  # Convert inches to feet
            ax.plot([start[0], end[0]], [start[1], end[1]], color='black', linewidth=1)
        elif entity.dxftype() == 'CIRCLE':
            center = (entity.dxf.center.x / 12, entity.dxf.center.y / 12)  # Convert inches to feet
            radius = entity.dxf.radius / 12  # Convert inches to feet
            circle = plt.Circle(center, radius, color='black', fill=False, linewidth=1)
            ax.add_artist(circle)
        elif entity.dxftype() == 'ARC':
            center = (entity.dxf.center.x / 12, entity.dxf.center.y / 12)  # Convert inches to feet
            radius = entity.dxf.radius / 12  # Convert inches to feet
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)
            arc = plt.Arc(center, 2 * radius, 2 * radius, 0, math.degrees(start_angle), math.degrees(end_angle), color='black', linewidth=1)
            ax.add_artist(arc)
        elif entity.dxftype() == 'TEXT':
            insert = (entity.dxf.insert.x / 12, entity.dxf.insert.y / 12)  # Convert inches to feet
            text = entity.dxf.text
            ax.text(insert[0], insert[1], text, fontsize=4, color='black')
        elif entity.dxftype() == 'MTEXT':
            insert = (entity.dxf.insert.x / 12, entity.dxf.insert.y / 12)  # Convert inches to feet
            text = entity.dxf.text
            ax.text(insert[0], insert[1], text, fontsize=4, color='black')

    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('X (feet)')
    ax.set_ylabel('Y (feet)')
    ax.set_title('Architectural Plan')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.tick_params(axis='both', direction='inout', which='both')
    
    # Set x and y axis ticks in feet
    x_ticks = [i * 10 for i in range(int(ax.get_xlim()[0] / 10), int(ax.get_xlim()[1] / 10) + 1)]
    y_ticks = [i * 10 for i in range(int(ax.get_ylim()[0] / 10), int(ax.get_ylim()[1] / 10) + 1)]
    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)
    
    # Create 'pdf' folder if it doesn't exist
    pdf_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf')
    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)
    
    # Generate PDF filename
    pdf_filename = os.path.join(pdf_folder, f"{os.path.basename(filename).replace('.dxf', '.pdf')}")
    
    # Save the plot as PDF
    with PdfPages(pdf_filename) as pdf:
        pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    return pdf_filename


filename = [
    os.path.join(data_folder, 'SMH_DXF1.dxf'),
    os.path.join(data_folder, 'SMH_DXF2.dxf'),
    os.path.join(data_folder, 'SMH_DXF3.dxf'),
    os.path.join(data_folder, 'SMH_DXF4.dxf'),
    os.path.join(data_folder, 'SMH_DXF5.dxf'),
    os.path.join(data_folder, 'SMH_DXF6.dxf'),
    os.path.join(data_folder, 'SMH_DXF7.dxf'),
    os.path.join(data_folder, 'SMH_DXF8.dxf'),
    os.path.join(data_folder, 'SMH_DXF9.dxf'),
    os.path.join(data_folder, 'SMH_DXF10.dxf'),
    os.path.join(data_folder, 'SMH_DXF11.dxf'),
    os.path.join(data_folder, 'SMH_DXF12.dxf'),
    os.path.join(data_folder, 'SMH_DXF13.dxf'),
    os.path.join(data_folder, 'SMH_DXF14.dxf'),
    os.path.join(data_folder, 'SMH_DXF15.dxf'),
    os.path.join(data_folder, 'SMH_DXF16.dxf'),
    os.path.join(data_folder, 'SMH_DXF21.dxf'),
    os.path.join(data_folder, 'SMH_DXF20.dxf'),
    os.path.join(data_folder, 'SMH_DXF19.dxf'),
    os.path.join(data_folder, 'SMH_DXF18.dxf'),
    os.path.join(data_folder, 'SMH_DXF17.dxf')
]


Data = Data_creation(filename)
nearest_neighbors, Differences = Similarity_fuc(new_point, Data)
sorted_point = nearest_neighbors.index.tolist()  # Convert index to list of file names


pdf_files = []
print(sorted_point)
for dxf_file in sorted_point:
    print(dxf_file)
    pdf_file = plot_dxf(dxf_file)
    pdf_files.append(pdf_file)

print(f"PDFs generated successfully: {pdf_files}")


