# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, json
from flask_bootstrap3 import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
import datetime


app = Flask(__name__)
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///monitoring.db'
db = SQLAlchemy(app)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), index=True, unique=True)
    status = db.Column(db.String(100), index=True)
    period = db.Column(db.Integer)
    last_update = db.Column(db.DateTime)

    def is_fresh(self, now):
        return self.period == 0 or \
            now - self.last_update < datetime.timedelta(seconds=self.period)

    def json_info(self):
        return json.dumps({'name': self.name,
                           'status': self.status,
                           'last_update': self.last_update})

    def json_status(self):
        return json.dumps({'status': self.status})

db.create_all()


BAD_REQUEST_ERROR = ('{"status": "Bad request"}', 400)
NOT_FOUND_ERROR = ('{"status": Service not found"}', 404)


@app.route('/')
def index():
    now = datetime.datetime.utcnow()
    tz_delta = datetime.datetime.now() - datetime.datetime.utcnow()
    services = [{'name': service.name,
                 'status': service.status,
                 'last_update': (service.last_update + tz_delta).strftime('%d.%m.%Y %H:%M'),
                 'ok': service.status == 'OK',
                 'fresh': service.is_fresh(now)} for service in Service.query.all()]
    return render_template('index_bs.html', services=services)


@app.route('/<int:service_id>/info')
def service_info(service_id):
    service = Service.query.get(service_id)
    if service is None:
        return NOT_FOUND_ERROR
    return service.json_info()


@app.route('/<int:service_id>/status')
def service_status(service_id):
    service = Service.query.get(service_id)
    if service is None:
        return NOT_FOUND_ERROR
    return service.json_status()


@app.route('/<int:service_id>/update', methods=['POST'])
def service_update(service_id):
    service = Service.query.get(service_id)
    if service is None:
        return NOT_FOUND_ERROR
    if request.headers['Content-Type'] != 'application/json':
        return BAD_REQUEST_ERROR
    try:
        status = request.json['Status']
    except KeyError:
        return BAD_REQUEST_ERROR
    service.status = status
    service.last_update = datetime.datetime.utcnow()
    db.session.commit()
    return '{"status": "OK"}'


@app.route('/register', methods=['POST'])
def service_register():
    if request.headers['Content-Type'] != 'application/json':
        return BAD_REQUEST_ERROR
    try:
        name = request.json['Name']
        period = int(request.json['Period'])
    except (KeyError, ValueError):
        return BAD_REQUEST_ERROR
    if Service.query.filter(Service.name == name).first() is not None:
        return BAD_REQUEST_ERROR
    now = datetime.datetime.utcnow()
    new_service = Service(name=name, status='OK', period=period, last_update=now)
    db.session.add(new_service)
    db.session.commit()
    return '{"status": "OK", "id": %d}' % new_service.id


if __name__ == '__main__':
    app.run()
