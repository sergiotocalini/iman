from datetime import date
from pony.orm import *

db = Database()

class User(db.Entity):
    _table_ = "users"
    id = PrimaryKey(int, auto=True)
    userid = Required(unicode)
    displayname = Required(unicode)
    email = Required(unicode, unique=True)
    password = Optional(unicode, nullable=True)
    avatar = Required(unicode)
    status = Required(bool, default=False)
    admin = Required(bool, default=False)
    acls = Set("Acl")
    centers = Set("Center")
    groups = Set("Group")
    
class Item(db.Entity):
    _table_ = "items"
    id = PrimaryKey(int, auto=True)
    serial = Required(unicode, unique=True)
    status = Required(bool)
    notes = Optional(unicode, nullable=True)
    product = Required("Product")
    center = Optional("Center")
    agreements = Set("Agreement")

    def expiration(self):
        last = date.today()
        for i in self.agreements:
            if i.expire_on > last:
                return i.expire_on
        return None

    def url(self):
        if self.center:
            url = {}
            url['serial'] = self.serial.lower()
            url['site'] = self.center.site.name[5:8].lower()
            url['country'] = self.center.site.name[0:2].lower()
            return self.product.management.format(**url)
        else:
            return None        
        
class Acl(db.Entity):
    _table_ = "acls"
    id = PrimaryKey(int, auto=True)
    sites = Set("Site")
    users = Set(User)
    groups = Set("Group")
    centers = Set("Center")
            
class Site(db.Entity):
    _table_ = "sites"
    id = PrimaryKey(int, auto=True)
    name = Required(unicode, unique=True)
    acls = Set(Acl)
    centers = Set("Center")
    
class Vendor(db.Entity):
    _table_ = "vendors"
    id = PrimaryKey(int, auto=True)
    name = Required(unicode, unique=True)
    telephone = Optional(unicode)
    mobile = Optional(unicode)
    email = Optional(unicode)
    comments = Optional(unicode)
    agreements = Set("Agreement")
    products = Set("Product")
    
class Group(db.Entity):
    _table_ = "groups"
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    gecos = Optional(unicode)
    users = Set(User)
    acls = Set(Acl)

class Agreement(db.Entity):
    _table_ = "agreements"
    id = PrimaryKey(int, auto=True)
    serial = Required(unicode, unique=True)
    create_on = Required(date)
    expire_on = Required(date)
    price = Optional(unicode)
    notes = Optional(unicode)
    items = Set(Item)
    vendor = Optional(Vendor)

class Config(db.Entity):
    _table_ = "configs"
    id = PrimaryKey(int, auto=True)
    key = Required(unicode, unique=True)
    value = Required(unicode)

class Center(db.Entity):
    _table_ = "centers"
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    site = Required("Site")
    items = Set(Item)
    acls = Set(Acl)
    owner = Required(User)
    
class Category(db.Entity):
    _table_ = "categories"
    id = PrimaryKey(int, auto=True)
    name = Required(unicode, unique=True)
    products = Set("Product")
    
class Product(db.Entity):
    _table_ = "products"
    id = PrimaryKey(int, auto=True)
    serial = Required(unicode, unique=True)
    model = Required(unicode)
    management = Optional(unicode)
    vendor = Optional(Vendor)
    items = Set(Item)
    categories = Set(Category)
    
