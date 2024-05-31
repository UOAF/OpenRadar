import math

# Another hint if you are converting BMS objective X /Y which are between 0-1023 (km) the conversion for km to feet is best used 
# with 3279.98 ft per km insteed of RL 3280.84 ft per km

FT_PER_DEGREE = 365221.8846
RADIANS_TO_DEGREE = 57.2957795
DEGREES_TO_RADIANS = 0.01745329
EARTH_RADIUS_FEET = 20925700


## Untested
def ll_to_xy(in_lat, in_lon):

    Theatre_Lat = 33.84375
    Theatre_Long = 123

    in_lat_true = in_lat - Theatre_Lat
    in_lon_true = in_lon - Theatre_Long

    true_lat_rad = in_lat_true * DEGREES_TO_RADIANS
    true_lon_rad = in_lon_true * DEGREES_TO_RADIANS

    lat_diff_feet = true_lat_rad * EARTH_RADIUS_FEET
    lon_diff_feet = true_lon_rad * EARTH_RADIUS_FEET * math.cos( true_lat_rad )

    x = lat_diff_feet
    y = lon_diff_feet

    return x, y
    
def xy_to_lla(input_North, input_East):

    # North and East in feet from the 0,0 X,y Plane

    # The Latitude and Longitude of the SW corner of the theater
    # in Degrees. Stored in MAP theater file.
    Theatre_Lat = 33.84375
    Theatre_Long = 123

    # Latitude in Radians
    outCoordLat = ( Theatre_Lat * FT_PER_DEGREE + input_North ) / EARTH_RADIUS_FEET
 
    # Cosine of Latitude
    cosLat = math.cos( outCoordLat )
 
    # Longitude in Radians
    outCoordLong = ( ( Theatre_Long * DEGREES_TO_RADIANS * EARTH_RADIUS_FEET * cosLat ) + input_East ) / ( EARTH_RADIUS_FEET * cosLat )
 
    # Converting to Degrees
    outCoordLat = outCoordLat * RADIANS_TO_DEGREE
    outCoordLong = outCoordLong * RADIANS_TO_DEGREE

    return outCoordLat, outCoordLong