from flask_mongoengine import Document
from mongoengine.fields import DictField, StringField, IntField, BooleanField, ListField


class Kernelspec(DictField):
    name = StringField(required=True, default='python3')
    display_name = StringField(required=True, default='Python 3')
    language = StringField()


class CodemirrorMode(DictField):
    name = StringField(required=True, default='ipython')
    version = IntField(required=True, default=3)


class LanguageInfo(DictField):
    name = StringField(required=True, default='python')
    file_extension = StringField()
    mimetype = StringField()
    nbconvert_exporter = StringField()
    pygments_lexer = StringField()
    version = StringField()
    codemirror_mode = DictField(
        CodemirrorMode(), default=CodemirrorMode,
        help_text='codemirror'
    )


class Metadata(DictField):
    kernelspec = DictField(
        Kernelspec(), required=True, help_text='kernelspec', default=Kernelspec
    )
    language_info = DictField(
        LanguageInfo(), required=True, help_text='language info',
        default=LanguageInfo
    )


class Cell(DictField):
    cell_type = StringField(required=True, default='code', help_text='cell type')
    metadata = DictField(help_text='cell metadata')
    source = StringField(required=True, default="print('hello')", help_text='source')
    outputs = ListField(DictField(), required=True, help_text='outputs', default=[DictField()])
    execution_count = IntField(help_text='exec count')


class Notebooks(Document):
    __project_regex__ = '^[a-zA-Z0-9_]+$'
    project = StringField(
        min_length=3, max_length=30, required=True, regex=__project_regex__,
        help_text="project name/slug (valid format: `{}`)".format(
            __project_regex__
        )
    )
    is_public = BooleanField(
        required=True, default=False, help_text='public or private notebook'
    )
    nbformat = IntField(default=4, help_text="nbformat version")
    nbformat_minor = IntField(default=2, help_text="nbformat minor version")
    metadata = DictField(Metadata(), help_text='notebook metadata')
    cells = ListField(Cell(), max_length=10, help_text='cells')
    meta = {'collection': 'notebooks', 'indexes': ['project', 'is_public']}

    problem_key = 'application/vnd.plotly.v1+json'
    escaped_key = problem_key.replace('.', '~dot~')

    def transform(self, incoming=True):
        if incoming:
            old_key = self.problem_key
            new_key = self.escaped_key
        else:
            old_key = self.escaped_key
            new_key = self.problem_key

        for cell in self.cells:
            for output in cell['outputs']:
                if old_key in output.get('data', {}):
                    output['data'][new_key] = output['data'].pop(old_key)

    def clean(self):
        self.transform()

    def restore(self):
        self.transform(incoming=False)
