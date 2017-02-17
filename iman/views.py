#!/usr/bin/env python
import os
from hashlib import md5
from datetime import datetime
import arrow
from functools import wraps
from flask import Flask, request, render_template, g, jsonify, json
from flask import url_for, abort, flash, redirect, session
from forms import *
from lib import *
from mavapa import mavapa, get_user_data

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, date):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

app = Flask(__name__, instance_relative_config=True)
app.config.from_object(os.environ['APP_SETTINGS'])
app.secret_key = app.config['SECRET_KEY']
app.json_encoder = CustomJSONEncoder
app.register_blueprint(mavapa, url_prefix='/oauth')
if not app.config.has_key('CDN_IMAN'):
    app.config['CDN_IMAN'] = '%s/static' %app.config.get('APPLICATION_ROOT', '')
if app.config['DB_TYPE'] == 'mysql':
    db.bind(app.config['DB_TYPE'], host=app.config['DB_HOST'],
            port=app.config['DB_PORT'], db=app.config['DB_NAME'],
            user=app.config['DB_USER'], passwd=app.config['DB_PASS'])
    db.generate_mapping(create_tables=True)
else:
    print('Database doesn\'t tested')
    exit(0)
sql_debug(app.config.get('DB_DEBUG', False))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session['access_token'] if 'access_token' in session else None
        user = session['user'] if 'user' in session else None
        if access_token is None or user is None:
            return redirect(url_for('mavapa.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    return session['user'].get('admin', False)

@db_session
def post_login():
    user = get_data('User', userid=session['user']['id'])
    if not user:
        user = User(userid=session['user']['id'],
                    email=session['user']['email'],
                    avatar=session['user']['avatar'],
                    displayname=session['user']['displayname'])
    else:
        user.set(email=session['user']['email'],
                 avatar=session['user']['avatar'],
                 displayname=session['user']['displayname'])
    session['user']['admin'] = user.admin
    session['user']['status'] = user.status
    commit()

@app.route('/fresh_u/')
def fresh_user():
    post_login()
    return redirect(url_for('index'))

@db_session
def get_data(table, **kwargs):
    if kwargs:
        return eval(table).get(**kwargs)
    else:
        return select(o for o in eval(table))
    
@app.context_processor
def custom_tools():
    def time_humanize(value):
        if isinstance(value, datetime):
            local = arrow.Arrow.fromdatetime(value)
        else:
            local = arrow.Arrow.fromdate(value)
        return local.humanize()

    def date_format(value, fmt='%d/%m/%Y'):
        local = '-'
        if value:
            if isinstance(value, datetime):
                local = datetime.strftime(value, fmt)
            else:
                local = date.strftime(value, fmt)
        return local

    def items_support():
        support = 0
        expired = 0
        items = get_data('Item')
        for i in items:
            if i.status and i.expiration():
                support += 1
            elif i.status:
                expired += 1
        return (('Supported', support), ('Expired', expired))
                
    return dict(data=get_data, ago=time_humanize, dformat=date_format, supported=items_support)

def active_user(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not session['user'].get('status', False):
            return redirect(url_for('unauthorized'))
        return f(*args, **kwargs)
    return decorated_func

@app.before_request
@db_session
def before_request():
    refresh_user = False
    if 'access_token' not in session:
        return
    if 'last_update' not in session:
        session['last_update'] = datetime.now()
        refresh_user = True
    else:
        if (datetime.now() - session['last_update']).seconds > 60:
            refresh_user = True
            session['last_update'] = datetime.now()
    if 'user' in session and refresh_user:
        mavapa_user = get_user_data(session)
        if mavapa_user:
            user = get_data('User', email=session['user']['email'])
            if user:
                session['user']['admin'] = user.admin
                session['user']['status'] = user.status
            else:
                post_login()
        else:
            return redirect(url_for('logout'))

@app.route('/')
@login_required
@active_user
@db_session
def index():
    return render_template('index.html')

@app.route('/admin', defaults={'mod': 'dash'})
@app.route('/admin/<mod>')
@login_required
@active_user
@db_session
def admin(mod):
    if mod == 'users':
        return render_template('admin_users.html')
    elif mod == 'sites':
        return render_template('admin_sites.html')
    elif mod == 'vendors':
        return render_template('admin_vendors.html')
    else:
        return render_template('admin_configs.html')

@app.route('/agreements')
@login_required
@active_user
@db_session
def agreements():
    return render_template('agreements.html')
    
@app.route('/favicon.ico')
def favicon():
    return redirect("%s/img/favicon.ico" %app.config['CDN_IMAN'])

@app.route('/profile')
@login_required
@active_user
def profile():
    return render_template('profile.html')

@app.route('/inventory')
@login_required
@active_user
@db_session
def inventory():
    return render_template('inventory.html')

@app.route('/contracts/<serial>', methods=['GET', 'POST'])
@login_required
@active_user
@db_session
def contracts(serial=None):
    if not serial:
        return redirect(url_for('agreements'))
    agree = get_data('Agreement', serial=serial) if serial != 'new' else None
    form = Contracts(request.form)
    form.vendor.choices = [(0, '')]+[(i.id, i.name) for i in get_data('Vendor')]
    if request.method == 'POST':
        if form.validate():
            vendor = get_data('Vendor', id=form.vendor.data)
            if agree:
                agree.set(serial=form.serial.data, price=form.price.data, vendor=vendor,
                          create_on=form.start.data, expire_on=form.end.data,
                          notes=form.notes.data)
                commit()
                flash('<strong>%s</strong>: Contract updated!' %form.serial.data, 'warning')
            else:
                agree = Agreement(serial=form.serial.data, price=form.price.data,
                                  vendor=vendor, notes=form.notes.data,
                                  create_on=form.start.data, expire_on=form.end.data)
                commit()
                flash('<strong>%s</strong>: Contract created!' %form.serial.data, 'success')
            return redirect(url_for('contracts', serial=agree.serial))
        else:
            flash('<strong>%s</strong>: Contract errors!' %form.serial.data, 'danger')
    if agree:
        form.serial.data = agree.serial
        form.price.data  = agree.price
        form.vendor.data = agree.vendor.id
        form.start.data  = agree.create_on
        form.end.data    = agree.expire_on
        form.notes.data  = agree.notes
    return render_template('contracts.html', form=form, serial=serial)
            
@app.route('/items/<serial>', methods=['GET', 'POST'])
@login_required
@active_user
@db_session
def items(serial=None):
    if not serial:
        return redirect(url_for('inventory'))
    item = get_data('Item', serial=serial) if serial != 'new' else None        
    form = Items(request.form)
    form.product.choices = [(0, '')]+[(i.id, '[%s] %s' %(i.serial,i.model)) for i in get_data('Product')]
    form.center.choices = [(0, '')]+[(i.id, '[%s] %s' %(i.site.name,i.name)) for i in get_data('Center')]
    if request.method == 'POST':
        if form.validate():
            center = get_data('Center', id=form.center.data)
            product = get_data('Product', id=form.product.data)
            if item:
                item.set(serial=form.serial.data, status=form.status.data,
                         notes=form.notes.data, product=product, center=center)
                commit()
                flash('<strong>%s</strong>: Item updated!' %form.serial.data, 'warning')
            else:
                item = Item(serial=form.serial.data, status=form.status.data,
                            notes=form.notes.data, product=product, center=center)
                commit()
                flash('<strong>%s</strong>: Item created!' %form.serial.data, 'success')
            if request.form.get('savenn', None):
                return redirect(url_for('items', serial="new"))
            return redirect(url_for('items', serial=item.serial))
        else:
            flash('<strong>%s</strong>: Item errors!' %form.serial.data, 'danger')
    if item:
        form.serial.data  = item.serial
        form.status.data  = item.status
        form.product.data = item.product.id
        form.center.data  = 0 if item.center is None else item.center.id
        form.notes.data   = item.notes

    return render_template('items.html', form=form, serial=serial)

@app.route('/logout')
def logout():
    return redirect(url_for('mavapa.logout'))

@app.route('/unauthorized')
def unauthorized():
    if not session['user'].get('status', False):
        return render_template('unauthorized.html')
    else:
        return redirect(url_for('index'))

@app.route('/api/<obj>', methods=['GET', 'POST', 'DELETE'])
@login_required
@active_user
@db_session
def api(obj):
    args = request.args.to_dict()
    if request.method == 'GET':
        if args:
            res = [get_data(obj, **args).to_dict()]
        else:
            res = [i.to_dict() for i in get_data(obj)]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST' and session['user']['admin']:
        if args:
            content = request.get_json(silent=True)
            odata = get_data(obj, **args)
            if odata and content:
                for i in content.keys():
                    if hasattr(odata, i):
                        attr = getattr(odata, i)
                        if isinstance(attr, pony.orm.core.SetInstance):
                            valdict = content[i].copy()
                            valdict.pop('action', None)
                            if content[i]['action'] == 'add':
                                if i == 'agreements':
                                    attr.add(Agreement.get(**valdict))
                                elif i == 'items':
                                    attr.add(Item.get(**valdict))
                            elif content[i]['action'] == 'del':
                                if i == 'agreements':
                                    attr.remove(Agreement.get(**valdict))
                                elif i == 'items':
                                    attr.remove(Item.get(**valdict))
                        else:
                            odata.set(**{i: content[i]})
                commit()
        else:
            res = []
        return jsonify(datetime=datetime.now())
    elif request.method == 'DELETE' and session['user']['admin']:
        if args:
            odata = get_data(obj, **args)
            if odata:
                odata.delete()
                commit()
                res = '200 - OK'
            else:
                res = '404 - Not found'
        return jsonify(datetime=datetime.now(), data=[res])

@app.route('/api/products', methods=['DELETE', 'GET', 'POST'])
@db_session
def api_products():
    args = request.args.to_dict()
    if request.method == 'GET':
        if args:
            res = []
            product = get_data('Product', **args)
            if product:
                data = product.to_dict()
                res.append(data)
        else:
            res = [i.to_dict() for i in get_data('Product')]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST':
        if is_admin():
            content = request.get_json(silent=True)
            if args.get('serial') or args.get('id'):
                product = get_data('Product', **args)
                if product:
                    product.set(**content)
                    commit()
                else:
                    abort(404)
            else:
                Product(**content)
                commit()
        else:
            abort(401)
    elif request.method == 'DELETE':
        if is_admin():
            if args.get('serial') or args.get('id'):
                product = get_data('Product', **args)
                if product:
                    product.delete()
                    commit()
                else:
                    abort(404)
            else:
                abort(400)
        else:
            abort(401)
    return jsonify(datetime=datetime.now())

@app.route('/api/vendors', methods=['DELETE', 'GET', 'POST'])
@db_session
def api_vendors():
    args = request.args.to_dict()
    if request.method == 'GET':
        if args:
            res = []
            vendor = get_data('Vendor', **args)
            if vendor:
                data = vendor.to_dict()
                res.append(data)
        else:
            res = [i.to_dict() for i in get_data('Vendor')]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST':
        if is_admin():
            content = request.get_json(silent=True)
            if args.get('name') or args.get('id'):
                vendor = get_data('Vendor', **args)
                if vendor:
                    vendor.set(**content)
                    commit()
                else:
                    abort(404)
            else:
                Vendor(**content)
                commit()
        else:
            abort(401)
    elif request.method == 'DELETE':
        if is_admin():
            if args.get('name') or args.get('id'):
                vendor = get_data('Vendor', **args)
                if vendor:
                    vendor.delete()
                    commit()
                else:
                    abort(404)
            else:
                abort(400)
        else:
            abort(401)
    return jsonify(datetime=datetime.now())

@app.route('/api/categories')
@db_session
def api_categories():
    args = request.args.to_dict()
    if request.method == 'GET':
        if args:
            res = []
            cat = get_data('Category', **args)
            if cat:
                data = cat.to_dict()
                res.append(data)
        else:
            res = [i.to_dict() for i in get_data('Category')]
        return jsonify(datetime=datetime.now(), data=res)
    return jsonify(datetime=datetime.now())

@app.route('/api/centers', methods=['DELETE', 'GET', 'POST'])
@db_session
def api_centers():
    args = request.args.to_dict()
    group_by = args.get('group_by')
    attrs = ['id', 'name']
    qf = dict((x, args[x]) for x in args if x in attrs)
    if request.method == 'GET':
        exclude = []
        if qf:
            res = []
            center = get_data('Center', **qf)
            if center:
                data = center.to_dict()
                res.append(data)
        else:
            if group_by == 'site':
                raw = select((c.site.name,c) for c in Center)
                res = {}
                for i in raw:
                    if not res.get(i[0]):
                        res[i[0]] = []
                    res[i[0]].append(i[1].to_dict())
            else:
                data = get_data('User')
                res = [i.to_dict(exclude=exclude) for i in data]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST':
        if is_admin():
            content = request.get_json(silent=True)
            if args.get('name') or args.get('id'):
                center = get_data('Center', **args)
                if center:
                    center.set(**content)
                    commit()
                else:
                    abort(404)
            else:
                Center(**content)
                commit()
        else:
            abort(401)
    elif request.method == 'DELETE':
        if is_admin():
            if args.get('name') or args.get('id'):
                center = get_data('Center', **args)
                if center:
                    center.delete()
                    commit()
                else:
                    abort(404)
            else:
                abort(400)
        else:
            abort(401)
    return jsonify(datetime=datetime.now())

@app.route('/api/sites', methods=['DELETE', 'GET', 'POST'])
@db_session
def api_sites():
    args = request.args.to_dict()
    if request.method == 'GET':
        if args:
            res = []
            site = get_data('Site', **args)
            if site:
                data = vendor.to_dict()
                res.append(data)
        else:
            res = [i.to_dict() for i in get_data('Site')]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST':
        if is_admin():
            content = request.get_json(silent=True)
            if args.get('name') or args.get('id'):
                site = get_data('Site', **args)
                if site:
                    site.set(**content)
                    commit()
                else:
                    abort(404)
            else:
                Site(**content)
                commit()
        else:
            abort(401)
    elif request.method == 'DELETE':
        if is_admin():
            if args.get('name') or args.get('id'):
                site = get_data('Site', **args)
                if site:
                    site.delete()
                    commit()
                else:
                    abort(404)
            else:
                abort(400)
        else:
            abort(401)
    return jsonify(datetime=datetime.now())

@app.route('/api/items', methods=['DELETE', 'GET', 'POST'])
@db_session
def api_items():
    args = request.args.to_dict()
    if request.method == 'GET':
        if args:
            res = []
            item = get_data('Item', **args)
            if item:
                data = item.to_dict()
                data['url'] = item.url()
                res.append(data)
        else:
            res = [i.to_dict() for i in get_data('Item')]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST':
        if is_admin():
            content = request.get_json(silent=True)
            if args.get('serial') or args.get('id'):
                item = get_data('Item', **args)
                if item:
                    item.set(**content)
                    commit()
                else:
                    abort(404)
            else:
                Item(**content)
                commit()
        else:
            abort(401)
    elif request.method == 'DELETE':
        if is_admin():
            if args.get('serial') or args.get('id'):
                item = get_data('Item', **args)
                if item:
                    item.delete()
                    commit()
                else:
                    abort(404)
            else:
                abort(400)
        else:
            abort(401)
    return jsonify(datetime=datetime.now())

@app.route('/api/users', methods=['DELETE', 'GET', 'POST'])
@db_session
def api_users():
    args = request.args.to_dict()
    order_by = args.get('order_by')
    attrs = ['id', 'userid', 'email']
    qf = dict((x, args[x]) for x in args if x in attrs)
    if request.method == 'GET':
        exclude = ['password']
        if qf:
            res = []
            user = get_data('User', **qf)
            if user:
                data = user.to_dict(exclude=exclude)
                res.append(data)
        else:
            if order_by == 'displayname':
                data = User.select().order_by(
                    User.displayname
                )
            elif order_by == 'email':
                data = User.select().order_by(
                    User.email
                )
            elif order_by == 'admin':
                data = User.select().order_by(
                    User.admin
                )
            else:
                data = get_data('User')
            res = [i.to_dict(exclude=exclude) for i in data]
        return jsonify(datetime=datetime.now(), data=res)
    elif request.method == 'POST':
        if is_admin():
            content = request.get_json(silent=True)
            if args.get('userid') or args.get('id'):
                user = get_data('User', **args)
                if user:
                    user.set(**content)
                    commit()
                else:
                    abort(404)
            else:
                User(**content)
                commit()
        else:
            abort(401)
    elif request.method == 'DELETE':
        if is_admin():
            if args.get('userid') or args.get('id'):
                user = get_data('User', **args)
                if user:
                    user.delete()
                    commit()
                else:
                    abort(404)
            else:
                abort(400)
        else:
            abort(401)
    return jsonify(datetime=datetime.now())

@app.route('/api/stats/centers')
@db_session
def api_stats_centers():
    args = request.args.to_dict()
    group_by = args.get('group_by')
    qf = dict((x, args[x]) for x in args if x in ['id','name'])
    if request.method == 'GET':
        res = []
        if qf:
            center = get_data('Center', **qf)
            if center:
                data = center.to_dict()
                data['site'] = center.site.to_dict()
                res.append(data)
        else:
            if not group_by:
                for center in get_data('Center'):
                    data = center.to_dict()
                    data['site'] = center.site.to_dict()
                    res.append(data)
            else:
                if group_by == 'site':
                    raw = select((c.site.name,c) for c in Center)
                    res = {}
                    for i in raw:
                        if not res.get(i[0]):
                            res[i[0]] = []
                        res[i[0]].append(i[1].to_dict())
            return jsonify(datetime=datetime.now(), data=res)
    return jsonify(datetime=datetime.now())    

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
    
if __name__ == "__main__":
    app.run('0.0.0.0', 7003)
