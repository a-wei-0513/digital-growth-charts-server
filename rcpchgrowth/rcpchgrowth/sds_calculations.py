import math
import statistics
import scipy.stats as stats
from scipy.interpolate import interp1d
# from scipy import interpolate  #see below, comment back in if swapping interpolation method
# from scipy.interpolate import CubicSpline #see below, comment back in if swapping interpolation method
import numpy as np
from datetime import date
import json
import pkg_resources
# import timeit #see below, comment back in if timing functions in this module


"""
dob: date of birth
obs_date: date of observation
sex: sex (string, MALE or FEMALE)
decimal_age: chronological, decimal
corrected_age: corrected for prematurity, decimal
measurement: height, weight, bmi, ofc (decimal)
observation: value (float)
gestation_weeks: gestational age(weeks), integer
gestation_days: supplementary days of gestation
lms: L, "male" or S
"""

#load the reference data
data = pkg_resources.resource_filename(__name__, "/data_tables/uk_who_0_20_preterm.json")
with open(data) as json_file:
            data = json.load(json_file)
            json_file.close()

# reference decimal ages
decimal_ages=[-0.325804244,-0.306639288,-0.287474333,-0.268309377,-0.249144422,-0.229979466,-0.210814511,-0.191649555,-0.1724846,-0.153319644,-0.134154689,-0.114989733,-0.095824778,-0.076659822,-0.057494867,-0.038329911,-0.019164956,0,0.019164956,0.038329911,0.038329911,0.057494867,0.076659822,0.083333333,0.095824778,0.114989733,0.134154689,0.153319644,0.166666667,0.1724846,0.191649555,0.210814511,0.229979466,0.249144422,0.25,0.333333333,0.416666667,0.5,0.583333333,0.666666667,0.75,0.833333333,0.916666667,1.0,1.083333333,1.166666667,1.25,1.333333333,1.416666667,1.5,1.583333333,1.666666667,1.75,1.833333333,1.916666667,2.0,2.0,2.083333333,2.166666667,2.25,2.333333333,2.416666667,2.5,2.583333333,2.666666667,2.75,2.833333333,2.916666667,3.0,3.083333333,3.166666667,3.25,3.333333333,3.416666667,3.5,3.583333333,3.666666667,3.75,3.833333333,3.916666667,4.0,4.0,4.083,4.167,4.25,4.333,4.417,4.5,4.583,4.667,4.75,4.833,4.917,5.0,5.083,5.167,5.25,5.333,5.417,5.5,5.583,5.667,5.75,5.833,5.917,6.0,6.083,6.167,6.25,6.333,6.417,6.5,6.583,6.667,6.75,6.833,6.917,7.0,7.083,7.167,7.25,7.333,7.417,7.5,7.583,7.667,7.75,7.833,7.917,8.0,8.083,8.167,8.25,8.333,8.417,8.5,8.583,8.667,8.75,8.833,8.917,9.0,9.083,9.167,9.25,9.333,9.417,9.5,9.583,9.667,9.75,9.833,9.917,10.0,10.083,10.167,10.25,10.333,10.417,10.5,10.583,10.667,10.75,10.833,10.917,11.0,11.083,11.167,11.25,11.333,11.417,11.5,11.583,11.667,11.75,11.833,11.917,12.0,12.083,12.167,12.25,12.333,12.417,12.5,12.583,12.667,12.75,12.833,12.917,13.0,13.083,13.167,13.25,13.333,13.417,13.5,13.583,13.667,13.75,13.833,13.917,14.0,14.083,14.167,14.25,14.333,14.417,14.5,14.583,14.667,14.75,14.833,14.917,15.0,15.083,15.167,15.25,15.333,15.417,15.5,15.583,15.667,15.75,15.833,15.917,16.0,16.083,16.167,16.25,16.333,16.417,16.5,16.583,16.667,16.75,16.833,16.917,17.0,17.083,17.167,17.25,17.333,17.417,17.5,17.583,17.667,17.75,17.833,17.917,18.0,18.083,18.167,18.25,18.333,18.417,18.5,18.583,18.667,18.75,18.833,18.917,19,19.083,19.167,19.25,19.333,19.417,19.5,19.583,19.667,19.75,19.833,19.917,20.0]


#public functions

def sds(age: float, measurement: str, measurement_value: float, sex: str)->float:
    """
    Public function
    Returns a standard deviation score. 
    Parameters are: 
    a decimal age (corrected or chronological), 
    a measurement (type of observation) ['height', 'weight', 'bmi', 'ofc']
    measurement_value (the value is standard units) [height and ofc are in cm, weight in kg bmi in kg/m2]
    sex (a standard string) ['male' or 'female']

    This function is specific to the UK-WHO data set as this is actually a blend of UK-90 and WHO 2006 references and necessarily has duplicate values.

    SDS is generated by passing the interpolated L, M and S values for age through an equation.
    Cubic interpolation is used for most values, but where ages of children are at the extremes of the growth reference,
    linear interpolation is used instead. These are:
    1. 23 weeks gestation
    2. 42 weeks gestation or 2 weeks post term delivery - the reference data here changes from UK90 to WHO 2006
    3. 2 years - children at this age stop being measured lying down and are instead measured standing, leading to a small decrease
    4. 4 years - the reference data here changes back to UK90 data
    5. 20 years - the threshold of the reference data

    Other considerations
     - Length data is not available until 25 weeks gestation, though weight date is available from 23 weeks
     - There is only BMI reference data from 2 weeks of age to aged 20y
     - Head circumference reference data is available from 23 weeks gestation to 17y in girls and 18y in boys
    """
    try:
        lms = get_lms(age, measurement, sex)
    except:
        raise Exception('Cannot calculate this value')
        print('Cannot calculate this value')
        
    l = lms['l']
    m = lms ['m']
    s = lms ['s']

    sds = z_score(l, m, s, measurement_value)
    return sds

def centile(z_score: float):
    """
    Converts a Z Score to a p value (2-tailed) using the SciPy library, which it returns as a percentage
    """

    centile = (stats.norm.cdf(z_score) * 100)
    return centile

def percentage_median_bmi( age: float, actual_bmi: float, sex: str)->float:

    """
    public method
    This returns a child's BMI expressed as a percentage of the median value for age and sex.
    It is used widely in the assessment of malnutrition particularly in children and young people with eating disorders.
    """
    
    age_index_one_below = nearest_age_below_index(age)

    if cubic_interpolation_possible(age, 'bmi', sex):
        m_one_below = data['measurement']["bmi"][sex][age_index_one_below]["M"]
        m_two_below = data['measurement']["bmi"][sex][age_index_one_below-1]["M"]
        m_one_above = data['measurement']["bmi"][sex][age_index_one_below+1]["M"]
        m_two_above = data['measurement']["bmi"][sex][age_index_one_below+2]["M"]
        
        m = cubic_interpolation(age, age_index_one_below, m_two_below, m_one_below, m_one_above, m_two_above)
    else:
        m_one_below = data['measurement']["bmi"][sex][age_index_one_below]["M"]
        m_one_above = data['measurement']["bmi"][sex][age_index_one_below+1]["M"]
        
        m = linear_interpolation(age, age_index_one_below, m_one_below, m_one_above)
    
    percent_median_bmi = (actual_bmi/m)*100.0
    return percent_median_bmi

def measurement_from_sds(measurement: str,  requested_sds: float,  sex: str,  decimal_age: float) -> float:
    """
    Public method
    Returns the measurement from a given SDS.
    Parameters are: 
        measurement (type of observation) ['height', 'weight', 'bmi', 'ofc']
        decimal age (corrected or chronological),
        requested_sds
        sex (a standard string) ['male' or 'female']

    Centile to SDS Conversion for Chart lines
    0.4th -2.67
    2nd -2.00
    9th -1.33
    25th -0.67
    50th 0
    75th 0.67
    91st 1.33
    98th 2.00
    99.6th 2.67
    """
    measurement_value = 0.0
    try:
        lms= get_lms(decimal_age, measurement, sex)
    except:
        print('Unable to get measurement from SDS')
    else:
        l = lms['l']
        m = lms['m']
        s = lms['s']

        if l != 0.0:
            measurement_value = math.pow((1+l*s*requested_sds),1/l)*m
        else:
            measurement_value = math.exp(s*requested_sds)*m
        return measurement_value

#private methods
def nearest_age_below_index(age: float)->int:
    """
    Returns the array index of the nearest (lowest) age (or a match) in the reference data below the calculated decimal age (either chronological or corrected for gestational age)
    Uses the NumPy library to do this quickly - identifies the first incidence of a value in a sorted array.
    """
    result_index = 0
    decimal_ages_as_np_array = np.asarray(decimal_ages)
    idx = np.searchsorted(decimal_ages_as_np_array, age, side="left")
    if idx > 0 and (idx == len(decimal_ages) or math.fabs(age - decimal_ages[idx-1]) < math.fabs(age - decimal_ages[idx])):
        result = decimal_ages[idx-1]
        result_index = idx-1
    else:
        result = decimal_ages[idx]
        result_index = idx
    if result <= age:
        return result_index
    else:
        return result_index-1

def cubic_interpolation_possible(age: float, measurement, sex):
    """
    See sds function. This method tests if the age of the child (either corrected for prematurity or chronological) is at a threshold of the reference data
    This method is specific to the UK-WHO data set.
    Thresholds wehere cubic interpolation is not possible:
    - Start of viability: [-0.325804244,-0.306639288....], indices are 0, 1
    - Threshold of UK90 term data and start of WHO data at 2 weeks of age (42 weeks): [...0,0.019164956,0.038329911,0.038329911,0.057494867...], indices are 17, 18, 19, 20, 21
    - Threshold at 2 years [1.916666667,2.0,2.0,2.083333333] - this is the same data set but children are measured standing not lying > 2y, indices 54, 55, 56, 57
    - Threshold of WHO 2006 data at 4y and reverts to UK90: [...3.916666667,4.0,4.0,4.083...], indices 79, 80, 81, 82
    - End of UK90 data set at 20y: [...19.917,20.0], indices 272, 273
    - Height in boys and girls below 27 weeks (no data below 25 weeks) [-0.2683093771] index 3
    - BMI in boys and girls below 4 weeks (no data below 2 weeks) [0.07665982204] index 22
    - OFC in boys > 17.917y index 248 (no data over 18y) or in girls > 16.917y index 236 (no data over 17y)
    """
    if age <= -0.306639288 or (age > 0.019164956 and age < 0.057494867) or (age > 1.916666667 and age < 2.083333333) or (age > 3.916666667 and age < 4.083) or age > 19.917 or (age < -0.2683093771 and measurement == 'height') or (age < 0.07665982204 and measurement == 'bmi') or (age > 17.917 and measurement == 'ofc' and sex=='male') or (age > 16.917 and measurement == 'ofc' and sex=='female'):
        return False
    else:
        return True


def get_lms(age: float, measurement: str, sex: str)->list:
    """
    Returns an interpolated L, M and S value as an array [l, m, s] against a decimal age, sex and measurement
    """
    
    try:
        #this child is < or > the extremes of the chart
        assert (age >= decimal_ages[0] or age <= decimal_ages[-1]), 'Cannot be younger than 23 weeks or older than 20y'
    except AssertionError as chart_extremes_msg:
        print(chart_extremes_msg)
    
    if measurement == 'height':
        try:
            #this child < 25 weeks and height is requested
            assert (age >= -0.287474333), 'There is no reference data for length below 25 weeks'
        except AssertionError as lower_length_threshold_error_message:
            print(lower_length_threshold_error_message)
    
    if measurement == 'bmi':
        try:
            #this child < 2 weeks and BMI is requested
            print(f'{measurement}')
            assert (age >= 0.038329911 and measurement == 'bmi'), 'There is no BMI reference data available for BMI below 2 weeks'
        except AssertionError as lower_bmi_threshold_error_message:
            print(lower_bmi_threshold_error_message)
    
    if measurement == 'ofc':
        try:
            #head circumference is requested and this child is either female > 17 or male >18y
            assert (measurement == 'ofc' and ((sex == 'male' and age <= 18.0) or (sex == 'female' and age <=17.0))), 'There is no head circumference data available in girls over 17y or boys over 18y'
        except AssertionError as upper_head_circumference_threshold_error_message:
            print(upper_head_circumference_threshold_error_message)

    age_index_one_below = nearest_age_below_index(age)
    if age == decimal_ages[age_index_one_below]:
        #child's age matches a reference age - no interpolation necessary
        l = data['measurement'][measurement][sex][age_index_one_below]["L"]
        m = data['measurement'][measurement][sex][age_index_one_below]["M"]
        s = data['measurement'][measurement][sex][age_index_one_below]["S"]
        lms = {
            'l': l,
            'm': m,
            's': s
        }
        return lms
        

    if cubic_interpolation_possible(age, measurement, sex):
        #collect all L, M and S above and below lower age index for cubic interpolation
        l_one_below = data['measurement'][measurement][sex][age_index_one_below]["L"]
        m_one_below = data['measurement'][measurement][sex][age_index_one_below]["M"]
        s_one_below = data['measurement'][measurement][sex][age_index_one_below]["S"]

        l_two_below = data['measurement'][measurement][sex][age_index_one_below-1]["L"]
        m_two_below = data['measurement'][measurement][sex][age_index_one_below-1]["M"]
        s_two_below = data['measurement'][measurement][sex][age_index_one_below-1]["S"]

        l_one_above = data['measurement'][measurement][sex][age_index_one_below+1]["L"]
        m_one_above = data['measurement'][measurement][sex][age_index_one_below+1]["M"]
        s_one_above = data['measurement'][measurement][sex][age_index_one_below+1]["S"]

        l_two_above = data['measurement'][measurement][sex][age_index_one_below+2]["L"]
        m_two_above = data['measurement'][measurement][sex][age_index_one_below+2]["M"]
        s_two_above = data['measurement'][measurement][sex][age_index_one_below+2]["S"]
        
        l = cubic_interpolation(age, age_index_one_below, l_two_below, l_one_below, l_one_above, l_two_above)
        m = cubic_interpolation(age, age_index_one_below, m_two_below, m_one_below, m_one_above, m_two_above)
        s = cubic_interpolation(age, age_index_one_below, s_two_below, s_one_below, s_one_above, s_two_above)
    else:
        #a chart threshold: collect one L, M and S above and below lower age index for linear interpolation
        l_one_below = data['measurement'][measurement][sex][age_index_one_below]["L"]
        m_one_below = data['measurement'][measurement][sex][age_index_one_below]["M"]
        s_one_below = data['measurement'][measurement][sex][age_index_one_below]["S"]

        l_one_above = data['measurement'][measurement][sex][age_index_one_below+1]["L"]
        m_one_above = data['measurement'][measurement][sex][age_index_one_below+1]["M"]
        s_one_above = data['measurement'][measurement][sex][age_index_one_below+1]["S"]

        l = linear_interpolation(age, age_index_one_below, l_one_below, l_one_above)
        m = linear_interpolation(age, age_index_one_below, m_one_below, m_one_above)
        s = linear_interpolation(age, age_index_one_below, s_one_below, s_one_above)
    # print(f"actual age: {round(age, 9)} l,m,s interpolated: {l} {m} {s} lower: {l_one_below} {m_one_below} {s_one_below}") #debugging as accuracy currently uncertain 
    # print(f"{l}, {m}, {s}")
    lms = {
        'l': l,
        'm': m,
        's': s
        }
    return lms

def cubic_interpolation( age: float, age_index_below: int, parameter_two_below: float, parameter_one_below: float, parameter_one_above: float, parameter_two_above: float) -> float:

    """
    See sds function. This method tests if the age of the child (either corrected for prematurity or chronological) is at a threshold of the reference data
    This method is specific to the UK-WHO data set.
    """

    cubic_interpolated_value = 0.0

    t = 0.0 #actual age ///This commented function is Tim Cole's used in LMSGrowth to perform cubic interpolation - 50000000 loops, best of 5: 7.37 nsec per loop
    tt0 = 0.0
    tt1 = 0.0
    tt2 = 0.0
    tt3 = 0.0

    t01 = 0.0
    t02 = 0.0
    t03 = 0.0
    t12 = 0.0
    t13 = 0.0
    t23 = 0.0

    age_two_below = decimal_ages[age_index_below-1]
    age_one_below = decimal_ages[age_index_below]
    age_one_above = decimal_ages[age_index_below+1]
    age_two_above = decimal_ages[age_index_below+2]
    
    t = age

    tt0 = t - age_two_below
    tt1 = t - age_one_below
    tt2 = t - age_one_above
    tt3 = t - age_two_above

    t01 = age_two_below - age_one_below
    t02 = age_two_below - age_one_above
    t03 = age_two_below - age_two_above

    t12 = age_one_below - age_one_above
    t13 = age_one_below - age_two_above
    t23 = age_one_above - age_two_above

    cubic_interpolated_value = parameter_two_below * tt1 * tt2 * tt3 /t01 / t02 / t03 - parameter_one_below * tt0 * tt2 * tt3 / t01 / t12 /t13 + parameter_one_above * tt0 * tt1 * tt3 / t02/ t12 / t23 - parameter_two_above * tt0 * tt1 * tt2 / t03 / t13 / t23

    # prerequisite arrays for either of below functions
    # xpoints = [decimal_ages[age_index_below-1], decimal_ages[age_index_below], decimal_ages[age_index_below+1], decimal_ages[age_index_below+2]]
    # ypoints = [parameter_two_below, parameter_one_below, parameter_one_above, parameter_two_above]

    # cs = CubicSpline(xpoints,ypoints,bc_type='natural')
    # cubic_interpolated_value = cs(age) # this also works, but not as accurate: 50000000 loops, best of 5: 7.42 nsec per loop

    # tck = interpolate.splrep(xpoints, ypoints)
    # cubic_interpolated_value = interpolate.splev(age, tck)   #Matches Tim Cole's for accuracy but slower: speed - 50000000 loops, best of 5: 7.62 nsec per loop

    return cubic_interpolated_value

def linear_interpolation( decimal_age: float, age_index_below: int, parameter_one_below: float, parameter_one_above: float) -> float:
    
    """
    See sds function. This method is to do linear interpolation of L, M and S values for children whose ages are at the threshold of the reference data, making cubic interpolation impossible
    """
    
    linear_interpolated_value = 0.0
    age_below = decimal_ages[age_index_below]
    age_above = decimal_ages[age_index_below+1]
    # linear_interpolated_value = parameter_one_above + (((decimal_age - age_below)*parameter_one_above-parameter_one_below))/(age_above-age_below)
    x_array = [age_below, age_above]
    y_array = [parameter_one_below, parameter_one_above]
    intermediate = interp1d(x_array, y_array)
    linear_interpolated_value = intermediate(decimal_age)
    return linear_interpolated_value

def z_score(l: float, m: float, s: float, observation: float):

    """
    Converts the (age-specific) L, M and S parameters into a z-score
    """
    sds = 0.0
    if l != 0.0:
        sds = (((math.pow((observation / m), l))-1)/(l*s))
    else:
        sds = (math.log(observation / m)/s)
    return sds

"""
These functions are for testing accuracy.
Commented out but left for documentation to show process behind evaluation of each interpolation method
# """                                                                                    
# def tim_tests():
# """
    # function to run growth data on 76 hypothetical children to test algorithm against gold standard (LMSGrowth and LMS2z function from Tim Cole R package Sitar)
# """

    # child_decimal_ages = [-0.249144422,-0.202600958,1.013004791,1.303216975,3.983572895,0.161533196,0.161533196,0,0.251882272,0.303901437,0.303901437,0.323066393,0.331279945,0.895277207,2.288843258,2.587268994,3.271731691,3.504449008,3.808350445,4.462696783,1.013004791,3.271731691,3.504449008,3.808350445,4.462696783,-0.095824778,0.396988364,0.793976728,1.065023956,1.330595483,1.492128679,2.280629706,2.565366188,0.396988364,0.793976728,1.065023956,0.323066393,0.380561259,0.41889117,0.676249144,0.887063655,0.898015058,1.095140315,1.45927447,1.535934292,1.708418891,1.919233402,0.380561259,0.676249144,0.887063655,1.095140315,1.45927447,1.535934292,1.708418891,1.919233402,1.327857632,1.984941821,2.691307324,2.746064339,3.244353183,3.422313484,4.164271047,4.878850103,4.955509925,5.032169747,5.278576318,5.708418891,5.935660507,6.127310062,6.412046543,1.327857632,2.691307324,4.164271047,4.878850103,5.708418891,5.935660507,6.127310062]
    # child_sexes = ["female","female","female","female","female","male","male","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","male","male","male","male","male","male","male","male","male","male","male","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","female","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male","male"]
    # child_measurements = ["weight","weight","height","height","height","weight","height","weight","weight","weight","height","height","weight","weight","weight","weight","weight","weight","weight","weight","height","height","height","height","height","weight","weight","weight","weight","weight","weight","weight","weight","height","height","height","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","height","height","height","height","height","height","height","height","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","weight","height","height","height","height","height","height","height"]
    # child_observations = [1.21,1.5,81,84.5,100.5,4.17,54.8,2.7,4.57,4.48,57,59,8.2,10.7,12.4,12.5,13.8,13.6,14.1,15.36,81,96,98,99.5,100.8,3.09,5.23,5.85,6.62,7.41,7.25,9.96,10.84,61.7,65,68.2,4.67,5.42,5.63,6.3,7.1,7.1,7.26,8.08,8.11,8.1,8.98,60,66,70.5,73.6,75.9,79.1,78.2,78.9,12.2,13.8,12.5,12.5,13.5,14.3,16,20.05,20.5,19.85,20.5,21.9,22.8,22.3,24,79.6,88,99,102.7,110,109.5,109]
    # child_gestational_ages = [27,27,27,27,27,35,35,40,40,40,40,40,27,27,27,27,27,27,27,27,27,27,27,27,27,35,35,35,35,35,35,35,35,35,35,35,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,40]
    # final_z_list=[]
    # final_uncorrected = []
    # for i in range(len(child_decimal_ages)):
        # z = sds(child_decimal_ages[i], child_measurements[i], child_observations[i], child_sexes[i])
        # final_z_list.append(z)
        # decimal_age_uncorrected = 
    # return final_z_list
# 
# def time_functions():
#   Used to test function run time. Needs timeit package importing also
    # return sds(-0.249144422,'weight',1.21,'female')

# def test_data():
#     array_to_add=[]
#     decimal_ages=[0.021902806,0.021902806,0.021902806,0.186173854,0.353182752,0.52019165,0.689938398,0.856947296,1.023956194,1.185489391,1.352498289,1.519507187,1.689253936,1.856262834,2.023271732,2.184804928,2.351813826,2.518822724,2.688569473,2.855578371,3.022587269,3.184120465,3.351129363,3.518138261,3.68788501,3.854893908,4.021902806,4.186173854,4.353182752,4.52019165,4.689938398,4.856947296,5.023956194,5.185489391,5.352498289,5.519507187,5.689253936,5.856262834,6.023271732,6.184804928]
#     measurement_types=["height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height","weight","ofc","height"]
#     for i in range(len(decimal_ages)):
#         value = measurement_from_sds(measurement_types[i], 0.67, 'male', decimal_ages[i])
#         array_to_add.append(value)
#     return array_to_add