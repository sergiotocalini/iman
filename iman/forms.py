#!/usr/bin/env python
from wtforms import Form, StringField, SubmitField, BooleanField, IntegerField
from wtforms import DateField, SelectField, TextAreaField
from wtforms.validators import Required, Email, Optional

class Items(Form):
    serial  = StringField('Serial', [Required()])
    status  = SelectField('Status', choices=[(1, 'Active'), (0, 'Inactive')], default=0, coerce=int)
    product = SelectField('Product', [Required()], choices=[(0, '')], default=0, coerce=int)
    center  = SelectField('Datacenter', [Required()], choices=[(0, '')], default=0, coerce=int)
    notes   = TextAreaField('Notes')
    save    = SubmitField('Save')
    savenn  = SubmitField('Save and continue')

class Contracts(Form):
    serial = StringField('Serial', [Required()])
    start  = DateField('Start', [Required()])
    end    = DateField('End', [Required()])
    price  = StringField('Price', [Required()])
    vendor = SelectField('Vendor', [Required()], choices=[(0, '')], default=0, coerce=int)
    notes  = TextAreaField('Notes')
    save   = SubmitField('Save')
    savenn = SubmitField('Save and continue')
    
