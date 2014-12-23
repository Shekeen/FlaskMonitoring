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

JSON_BAD_REQUEST_ERROR = ('{"status": "Bad request"}', 400)
JSON_NOT_FOUND_ERROR = ('{"status": Service not found"}', 404)


@app.route('/')
def index():
    now = datetime.datetime.utcnow()
    tz_delta = datetime.datetime.now() - datetime.datetime.utcnow()
    services = [{'id': service.id,
                 'name': service.name,
                 'status': service.status if len(service.status) <= 6 else service.status[:6],
                 'last_update': (service.last_update + tz_delta).strftime('%d.%m.%Y %H:%M'),
                 'ok': service.status == 'OK',
                 'fresh': service.is_fresh(now)} for service in Service.query.all()]
    return render_template('index.html', services=services)


@app.route('/<int:service_id>/info')
def service_info(service_id):
    now = datetime.datetime.utcnow()
    tz_delta = datetime.datetime.now() - datetime.datetime.utcnow()
    service = Service.query.get(service_id)
    if service is None:
        return render_template('404.html'), 404
    service = {
        'name': service.name,
        'status': service.status,
        'last_update': (service.last_update + tz_delta).strftime('%d.%m.%Y %H:%M'),
        'period': service.period,
        'ok': service.status == 'OK',
        'fresh': service.is_fresh(now)
    }
    return render_template('info.html', service=service)


@app.route('/api/json/<int:service_id>/info', methods=['GET'])
def service_info_json(service_id):
    service = Service.query.get(service_id)
    if service is None:
        return JSON_NOT_FOUND_ERROR
    return service.json_info()


@app.route('/api/json/<int:service_id>/status', methods=['GET'])
def service_status_json(service_id):
    service = Service.query.get(service_id)
    if service is None:
        return JSON_NOT_FOUND_ERROR
    return service.json_status()


@app.route('/api/json/<int:service_id>/update', methods=['POST'])
def service_update_json(service_id):
    service = Service.query.get(service_id)
    if service is None:
        return JSON_NOT_FOUND_ERROR
    if request.headers['Content-Type'] != 'application/json':
        return JSON_BAD_REQUEST_ERROR
    try:
        status = request.json['Status']
    except KeyError:
        return JSON_BAD_REQUEST_ERROR
    service.status = status
    service.last_update = datetime.datetime.utcnow()
    db.session.commit()
    return '{"status": "OK"}'


@app.route('/api/json/register', methods=['POST'])
def service_register_json():
    if request.headers['Content-Type'] != 'application/json':
        return JSON_BAD_REQUEST_ERROR
    try:
        name = request.json['Name']
        period = int(request.json['Period'])
    except (KeyError, ValueError):
        return JSON_BAD_REQUEST_ERROR
    if Service.query.filter(Service.name == name).first() is not None:
        return JSON_BAD_REQUEST_ERROR
    now = datetime.datetime.utcnow()
    new_service = Service(name=name, status='OK', period=period, last_update=now)
    db.session.add(new_service)
    db.session.commit()
    return '{"status": "OK", "id": %d}' % new_service.id


if __name__ == '__main__':
    app.run()
