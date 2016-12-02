from Managers import sourceManager, sinkManager
import utils
import re 
from loggers import man_log
import pyodbc

class WtpSource(sourceManager):
    ''' this is used to pull data and stuff from the wtp database 
        or yaml files defining the instruments and things 
    '''

    def __init__(self):
        sourceManager.__init__(self)
        self.template_fields['id'] = 'wtp id'
        self.template_fields['col_name'] = 'wtp name'
        self.template_fields['col_range'] = 'wtp range'
        self.template_fields['missing_vals'] = 'wtp missing value'
        self.data = None

    def _get_fieldnames_(self, desc):
        fieldnames = []
        for column in desc:
            fieldnames.append(column[0])
        return fieldnames

    def _read_data_(self):
        '''
        Follow the api for read data
        :return:
        '''
        data = []
        tablename = "user_3_disc_091509"
        con = pyodbc.connect("DSN=wtp_data")
        select_cmd = "select * from {0}".format(tablename)
        cursor = con.cursor()
        cursor.execute(select_cmd)
        desc = cursor.description
        fieldnames = self._get_fieldnames_(desc)

        # assert the file has all the expected fields
        man_log.debug('expected fieldnames: %s' % self.col_defs)
        for col_name in self.col_defs:
            if col_name not in fieldnames:
                raise self.TemplateError(('expected column %s not '
                                          'found in source datafile, with fields: %s') % (
                                             col_name, list(fieldnames)))

        sql_data = cursor.fetchall()
        # load each row
        for rowid, datarow in enumerate(sql_data):
            man_log.info('loading row %s' % rowid)
            man_log.debug('parsing row %s : %s' % (rowid, datarow))
            row = utils.OrderedDict()
            for col in self.col_defs:
                try:
                    # Find the data position due to the fact that you can only access the data in datarow
                    # with index
                    col_name = col.col_name
                    index = fieldnames.index(col_name)

                    # prepare parser
                    col_parser_name = 'parse_' + str(col)
                    man_log.debug('parsing %s from %s using %s' % (col,
                                                                   datarow[index], col_parser_name))
                    col_parser = getattr(self, col_parser_name,
                                         self.default_parser)



                    # I parse everything into datarow
                    row[col] = col_parser(str(datarow[index]), col)
                except Exception as e:
                    man_log.debug('Exception while parsing %s: %s' % (col, e))
                    row[col] = self.NoDataError('%s' % e)
            data.append(row)
        con.close()
        return data