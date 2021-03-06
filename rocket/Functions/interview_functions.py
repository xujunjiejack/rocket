"""
    This file should contain the function that works for getting data from wtp_data database about personal information.
    Couple assumptions need to be clarified:
       1: GUID information will not get pulled from the coinsPersonal.tmp, it should get data direct from database
          table: gen_rdmr_guid.
          if twin number is 3, then it's a caregiver.

       2: Gender and DOB information will also not get pulled from coinsPersonal.tmp. It should get data direct
          from "gen_twin" for twin. (But I don't know where pull data from for caregiver)

       3: use pyodbc to connect with the database, DSN = wtp_data

       4: each operation will open a connection and close at the end (Let's change if there is performance issue)

"""

from Functions.function_api import Function, DropRowFunction
from Managers import ssManager
import pyodbc
from dateutil import relativedelta
from datetime import datetime
from error_generator import user_error_log

guid_table = "gen_rdmr_guid"
rdoc_info = "user_jj_rdoc_ppt_info"
def get_open_connection():
    return pyodbc.connect("DSN=wtp_data")


class FindGuidByWTPInt(DropRowFunction):
    """
        This function accepts two possible keys: one is the combination of familyid and twin, and the other is just
         familyid

        The first combination will be seen as twin, suggesting that their twin number will be either 1 or 2
        The second option will be seen as caregiver, suggesting that its twin number will be 3 in gen_family_guid

    """
    argument_number = 2

    def get_name(self):
        return "findGuidByWTPInt"

    def get_documentation(self):
        return super().get_documentation()

    def _func_(self, data_list, args=None):

        if len(data_list) != 1 and len(data_list) !=2:
            raise Exception("data_list should be length of 1 or 2")

        if len(data_list) == 1:
            return self._get_guid_for_familyid_and_twin(familyid=data_list[0], twin=3)
        else:
            return self._get_guid_for_familyid_and_twin(familyid=data_list[0], twin=data_list[1])

    def _get_guid_for_familyid_and_twin(self, familyid, twin):
        con = get_open_connection()
        cur = con.cursor()
        sql = "SELECT guid from {0} WHERE familyid = '{1}' AND twin = {2};".format(guid_table, familyid, twin)
        cur.execute(sql)
        rows = cur.fetchmany()
        if len(rows) > 1:
            raise Exception("Duplicate guid for caregiver. familyid: {0}".format(familyid))
        if len(rows) == 0:
            raise Exception("No guid for familyid: %s, twin: %s" %(familyid, twin))
        con.close()
        # example rows will look like this [('NDARDM306PUU',)]
        return rows[0][0]



class FindGenderByWTPInt(Function):

    argument_number = 2

    # this mapping defines how to translate our database coding to NDAR requirement
    gender_mapping = {
        1 : "F",
        2 : "M",
        9998 : ssManager.NoDataError("Empty gender")

    }

    def _func_(self, data_list, args=None):
        if len(data_list) != 1 and len(data_list) !=2:
            raise Exception("data_list should be length of 1 or 2")

        if len(data_list) == 1:
            # Use data_r1_tr to decide the gender for caregiver
            gender = self._get_gender_(familyid=data_list[0], twin=3)
            return self.gender_mapping[int(gender)]
        else:
            gender = self._get_gender_(familyid=data_list[0], twin=data_list[1])
            return self.gender_mapping[int(gender)]

    def _get_gender_(self, familyid, twin):
        con = get_open_connection()
        cur = con.cursor()
        sql = "SELECT gender FROM {0} WHERE familyid = '{1}' AND twin = {2}".format(rdoc_info, familyid, twin)
        cur.execute(sql)

        rows = cur.fetchmany()
        if len(rows) > 1:
            raise Exception("Duplicate gender for caregiver. familyid: {0}".format(familyid))
        if len(rows) == 0:
            raise Exception("No gender for familyid: %s, twin: %s" % (familyid, twin))
        con.close()
        return rows[0][0]


    def get_documentation(self):
        return "Find gender given the familyid and twin or just familyid. Twin should always follow familyid"

    def get_name(self):
        return "findGenderByWTPInt"


class FindAgeByWTPInt(Function):
    """
        This functions represents the function that gets the age for a twin or caregiver based on the key
        It fetches the assessment date from data_r1_tr column "twadps". It fetches the dob from gen_twin column dateofbirth
        for twin.
        Then use the function to calculate the age.
    """

    argument_number = 2

    def get_name(self):
        return "findAgeByWTPInt"

    def _func_(self, data_list, args=None):
        if len(data_list) != 1 and len(data_list) !=2:
            raise Exception("data_list should be length of 1 or 2")

        if len(data_list) == 1:
            # decide parent gender
            # then decide whether i should mother dob or father dob
            #
            dob_date = self._get_birth_date_ (familyid=data_list[0], twin=3)

            if dob_date is None:
                return ssManager.NoDataError()

            assessment = self._get_assessment_date_(familyid=data_list[0])
            return self._calculate_age_(dob_date, assessment)

        else:
            dob_date = self._get_birth_date_(familyid=data_list[0], twin=data_list[1])
            if dob_date is None:
                return ssManager.NoDataError()
            assessment_date = self._get_assessment_date_(familyid=data_list[0])
            return self._calculate_age_(dob_date,assessment_date)

    def _get_birth_date_(self, familyid, twin):
        con = get_open_connection()
        cur = con.cursor()
        sql = "SELECT dateofbirth FROM {0} WHERE familyid = '{1}' AND twin = {2} ;".format(rdoc_info, familyid, twin)
        cur.execute(sql)
        rows = cur.fetchmany()
        if len(rows) > 1:
            raise Exception("Duplicate dob for twin: familyid: {0}, twin: {1}".format(familyid, twin))
        if len(rows) == 0:
            raise Exception("No dob for familyid: %s" % familyid)
        con.close()
        date_string = rows[0][0]
        if date_string == "9998":
            raise Exception("NoDOBDataForParticipant")
        return datetime.strptime(date_string, '%m/%d/%Y')

    def _get_assessment_date_(self, familyid):
        con = get_open_connection()
        cur = con.cursor()
        sql = "SELECT twadps FROM data_r1_tr WHERE familyid = '{0}';".format(familyid)
        cur.execute(sql)
        rows = cur.fetchmany()
        if len(rows) > 1:
            raise Exception("Duplicate dob for twin: familyid: {0}".format(familyid))
        if len(rows) == 0:
            raise Exception("No guid for familyid: %s " %familyid)
        con.close()
        date_string = rows[0][0]

        if date_string == "9998":
            raise Exception("NoAssessDataForParticipant")

        return datetime.strptime(date_string, '%m/%d/%Y')

    def _calculate_age_(self, olddate, recentdate):
        age = relativedelta.relativedelta(olddate, recentdate)
        year = abs(age.years)
        month = abs(age.months)
        day = abs(age.days)
        if day > 15:
            month = month + 1

        total_months = year * 12 + month
        return total_months

    def get_documentation(self):
        return "return the age given the familyid and twin or just familyid. Twin should always follow familyid"


class FindAssessByWTPInt(Function):

    argument_number = 2

    def get_name(self):
        return "findAssessDateByWTPInt"

    def get_documentation(self):
        return "Given the familyid and twin or just familyid. it will give you interview date string, like 09/30/1995"

    def _get_assessment_date_(self, familyid):
        con = get_open_connection()
        cur = con.cursor()
        sql = "SELECT twadps FROM data_r1_tr WHERE familyid = '{0}';".format(familyid)
        cur.execute(sql)
        rows = cur.fetchmany()
        if len(rows) > 1:
            raise Exception("Duplicate assessment date for twin: familyid: {0}".format(familyid))
        if len(rows) == 0:
            raise Exception("No assessment date for familyid: %s " %familyid)
        con.close()
        date_string = rows[0][0]

        if date_string == "9998":
            raise Exception("NoAssessDataForParticipant")

        return date_string

    def _func_(self, data_list, args=None):
        if len(data_list) != 1 and len(data_list) != 2:
            raise Exception("data_list should be length of 1 or 2")

        return self._get_assessment_date_(data_list[0])


class FindUrsiByWTPInt(Function):
    def get_name(self):
        return "findUrsiByWTPInt"

    def _func_(self, data_list, args=None):

        # if the data_list has one element, it's just for family
        if len(data_list) == 1:
            return self.get_ursi_from_wtpdata(data_list[0], 3)
        elif len(data_list) == 2: # if the data_list has two elements, it's for twin
            return self.get_ursi_from_wtpdata(data_list[0], data_list[1])
        else:
            raise Exception("data_list should be length of 1 or 2")

    def get_ursi_from_wtpdata(self, familyid, twin):
        con = get_open_connection()
        cur = con.cursor()
        sql = "SELECT ursi FROM {table} WHERE familyid = '{familyid}' and twin = {twin}"\
            .format(table = guid_table, familyid = familyid, twin = twin)
        cur.execute(sql)
        rows = cur.fetchmany()
        if len(rows) > 1:
            raise Exception("Duplicate ursi for twin: familyid: {0}".format(familyid))
        if len(rows) == 0:
            raise Exception("No ursi for familyid: %s " % familyid)
        con.close()
        ursi = rows[0][0]

        if ursi == "9998":
            return ssManager.NoDataError("Empty ursi")
        return ursi

    def get_documentation(self):
        return "Given the familyid and twin or just familyid, it will return you its ursi," \
               " the unique identifier used by COINS"


class FindWbicByWTPInt(Function):
    argument_number = 2

    def get_name(self):
        return "findWbicByWTPInt"

    def _func_(self, data_list, args=None):
        if len(data_list) != 1 and len(data_list) != 2:
            raise Exception("data_list should be length of 1 or 2")

        if len(data_list) == 1:
            return data_list[0][3:] + "3"

        if len(data_list) == 2:
            return data_list[0][3:] + str(data_list[1])

    def get_documentation(self):
        return "Given the familyid and twin or just familyid, it will return you its wbic, used by Goldsmith lab"


class GenderResponse(Function):
    def get_name(self):
        return "genderResponse"

    def _func_(self, data_list, args=None):
        # the mapper will look like this. 1,2,{0} This denotes that the data corresponding with the first data will be
        # used in the female, and the data corresponding with the second will be used when the data corresponding to the
        # third column indicates male

        # This function should have 3 argumennts
        if len(data_list) != 3:
           # user_error_log.log_mapping_error("Gender Response should contain 3 mapping files")
            return ssManager.NoDataError("Gender Response should contain 3 mapping files")

        # The male is "M", and "F" stands for female
        if data_list[2].strip() == "F":
            return data_list[0]
        elif data_list[2].strip() == "M":
            return data_list[1]
        else:
            return ssManager.NoDataError()

    def get_documentation(self):
        return "This method will choose one of the mapper column based on gender indicated by another column. In the " \
               "mapping, you need to provide with 3 arguments. The third one is used as the indicator for gender. The " \
               "first column will be used if the indicator shows 'F' (female) and the second column will be used if 'M'(Male)"

