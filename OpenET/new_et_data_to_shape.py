import os, sys
import time
import ee
from osgeo import ogr
from osgeo import osr

def reduceRegions(ee_img, featColl, scale, proj):
    ee_reducedFeatColl = ee_img.reduceRegions(
        collection=featColl,
        reducer=ee.Reducer.mean(),
        scale=scale,
        tileScale=1,
        crs=proj
    )
    aa_data= ee_reducedFeatColl.aggregate_array('mean').getInfo()
    # aa_data= ee_reducedFeatColl.getInfo()
    return aa_data

def write_shapefile(inShapefile, omit_fields, outDir, outShapefile, new_proj,  new_field_names, new_field_data):
    '''

    :param inShapeFile: shapefile to be copied and extended
    :param outDir:
    :param outfileName: name outShapefile
    :param omit_fields: inShapefile fields that will not be copied
    :param new_feat_names: et feature names
    :param new_feat_data: et feature data
    :return:
    '''
    # Get the input Layer
    inShapefile = "/Users/bdaudert/DATA/OpenET/Central_Valley/shapefiles/base15_ca_poly_170616.shp"
    inDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDataSource = inDriver.Open(inShapefile, 0)
    inLayer = inDataSource.GetLayer()
    # inLayer.SetAttributeFilter("minor = 'HYDR'")

    # set spatial reference and transformation
    sourceprj = inLayer.GetSpatialRef()
    targetprj = osr.SpatialReference()
    targetprj.ImportFromEPSG(new_proj)
    transform = osr.CoordinateTransformation(sourceprj, targetprj)

    # Create the output LayerS
    outShapefile = os.path.join("test_files", "base15_ca_poly_170616_DATA.shp" )
    outDriver = ogr.GetDriverByName("ESRI Shapefile")

    # Remove output shapefile if it already exists
    if os.path.exists(outShapefile):
        outDriver.DeleteDataSource(outShapefile)

    # Create the output shapefile
    outDataSource = outDriver.CreateDataSource(outShapefile)
    out_lyr_name = os.path.splitext(os.path.split(outShapefile)[1])[0]
    outLayer = outDataSource.CreateLayer(out_lyr_name, targetprj, geom_type=ogr.wkbMultiPolygon)

    # Add input Layer Fields to the output Layer if it is the one we want
    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        fieldName = fieldDefn.GetName()

        if omit_fields and fieldName in omit_fields:
            continue
        outLayer.CreateField(fieldDefn)

    for field_name in new_field_names:
        outLayer.CreateField(ogr.FieldDefn(field_name, ogr.OFTReal))

    # Get the output Layer's Feature Definition
    outLayerDefn = outLayer.GetLayerDefn()

    # Add features to the ouput Layer
    for k, inFeature in enumerate(inLayer):
        # Create output Feature
        outFeature = ogr.Feature(outLayerDefn)

        # Add field values from input Layer
        for i in range(0, outLayerDefn.GetFieldCount()):
            # Add pre-existing fields
            fieldDefn = outLayerDefn.GetFieldDefn(i)
            fieldName = fieldDefn.GetName()
            if omit_fields and fieldName in omit_fields:
                continue
            fieldVal = inFeature.GetField(i)
            if isinstance(fieldVal, float):
                fieldVal = round(fieldVal, 4)
            outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), fieldVal)


        # Add the etdata
        for j in range(len(new_field_names)):
            feat_name = new_field_names[j]
            val = new_field_data[j][k]
            if abs(val) < 0.0001:
                outFeature.SetField(feat_name, -9999.0)
            else:
                outFeature.SetField(feat_name, val)


        # Set geometry
        geom = inFeature.GetGeometryRef()
        # outFeature.SetGeometry(geom.Clone())

        # NEW
        geom.Transform(transform)
        new_geom = ogr.CreateGeometryFromWkb(geom.ExportToWkb())
        outFeature.SetGeometry(new_geom)
        # END NEW

        # Add new feature to output Layer
        outLayer.CreateFeature(outFeature)

    # Close DataSources
    inDataSource.Destroy()
    outDataSource.Destroy()

if __name__ == '__main__':
    omit_fields = []
    inShapefile = '/Users/bdaudert/DATA/OpenET/Central_Valley/shapefiles/base15_ca_poly_170616.shp'
    outDir = 'test_files'
    outShapefile = 'base15_ca_poly_170616_DATA.shp'
    ee.Initialize()
    year = '2017'
    start = year + '-01-01'
    end = year + '-12-31'
    proj = 'EPSG:4326'
    new_proj = 4326
    scale = 30
    var_name = 'et_actual'
    featColl = ee.FeatureCollection('users/bdaudert/base15_ca_poly_170616')
    field_names = []
    field_data = []
    omit_fields = []

    start_time = time.time()
    coll_name = 'projects/usgs-ssebop/et/conus/monthly/v0'
    ee_coll = ee.ImageCollection(coll_name). \
        filterDate(start, end).select(var_name)
    '''
    print('Getting monthly data')
    for m_int in range(1,13):
        m_str = str(m_int)
        if len(m_str) < 10:
            m_str = '0' + m_str
        feat_names.append('et_' + year + '_' + m_str)
        ee_img = ee.Image(ee_coll.filter(ee.Filter.calendarRange(m_int, m_int, 'month')).sum().unmask())
        feat_data.append(reduceRegions(ee_img, featColl, scale, proj)) 
    '''


    print('Getting annual data')
    field_names.append('et_' + year)
    coll_name = 'projects/usgs-ssebop/et/conus/annual/v1'
    ee_img = ee.Image(ee.ImageCollection(coll_name). \
                      filterDate(start, end).select(var_name).sum().unmask())
    field_data.append(reduceRegions(ee_img, featColl, scale, proj))


    write_shapefile(inShapefile, omit_fields, outDir, outShapefile, new_proj, field_names, field_data)