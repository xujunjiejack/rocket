from Managers import sourceManager, sinkManager
from MappingManager import MappingManager
import utils


class controller(object):
    ''' this class is aware of all three types of managers.
        source sink and mapping.
        this takes the responsibility of orchestrating the whole
        mapping from sinkt to source.

        I'm thinking about add a task manager to help user schedule a convert plan, so that
        many tasks can run automatically without people monitoring it
        Also I need to implement more functions for the program
    '''

    def __init__(self, mappingmanager):
        ''' this initializes the controller
            it takes a referance to a sourceManager and a sinkManager
            class. they shold be classes not instances.
            I will call them thank you very much.
        '''
        self.mapper = mappingmanager()

    def make_template(self):
        ''' this makes a new template.
            it will require both the source and sink schemas
            as they will be used by the mapping manager to
            create the template
        '''
        self.mapper.make_template()

    def do_convert(self, template_path=None):
        ''' this takes an existing template and asks the
            mapping manager to parse it using the source and sink
            managers
        '''

        # parse the template, setting up src and sink
        # different managers will prompt the user for what they need when they
        # need it. So I don't have to do it here
        self.mapper.parse_template()

        # the source manager will extract the data from the designated source
        self.mapper.load_source_data()

        # fill sink with converted data from source
        self.mapper.convert()

        return self.mapper.sink.write_outfile()
