import datetime
import logging
import sys
import time

import boto3
from flask import Flask, render_template, request
from flask_dynamo import Dynamo
import mistune
from yubico_client import Yubico


app = Flask(__name__)
app.config['DYNAMO_TABLES'] = [
    {
         'TableName': 'posts',
         'KeySchema': [
             dict(AttributeName='id', KeyType='HASH')
         ],
         'AttributeDefinitions': [
             dict(AttributeName='id', AttributeType='N')
         ],
         'ProvisionedThroughput': dict(ReadCapacityUnits=5, WriteCapacityUnits=5)
    }
]

dynamo = Dynamo(app)


@app.route("/")
def posts():
    posts = dynamo.tables['posts'].scan()['Items']
    logging.info(posts)
    posts.sort(key=lambda item:item['date'], reverse=True)
    return render_template('posts.html', posts=posts)


@app.route('/post/<id>')
@app.route('/<id>')
def post(id):
    try:
        post = dynamo.tables['posts'].get_item(
            Key={ 'id': int(id) }
        )['Item']

    except KeyError:
        response = ('', 404)

    else:
        post['html'] = mistune.markdown(post['content'])
        response = render_template('post.html', post=post)

    return response


@app.route('/posts/<id>/edit', methods=['GET', 'POST'])
@app.route('/<id>/edit', methods=['GET', 'POST'])
def edit(id):
    if request.method == 'POST':
        try:
            verify_otp(request.form['otp'])

        except ValueError:
            response = ('', 400)

        else:
            dynamo.tables['posts'].update_item(
                Key={ 'id': int(id) },
                UpdateExpression='SET edit = :edit, title = :title, content = :content',
                ExpressionAttributeValues={
                    ':edit': datetime.datetime.now().strftime("%Y-%m-%d"),
                    ':title': request.form['title'].strip(),
                    ':content': request.form['content']
                }
            )

        response = '=)'
           

    else:
        try:
            post = dynamo.tables['posts'].get_item(
                Key={ 'id': int(id) }
            )['Item']

        except KeyError:
            response = ('', 404)

        else:
            response = render_template('edit.html', post=post)

    return response


@app.route('/post/<id>/delete', methods=['GET', 'POST'])
@app.route('/<id>/delete', methods=['GET', 'POST'])
def delete(id):
    if request.method == 'POST':
        try:
            verify_otp(request.form['otp'])

        except ValueError:
            response = ('', 400)

        else:
            dynamo.tables['posts'].delete_item(
                Key={
                    'id': int(id)
                }
            )
            response = '=)'

    else:
        response = render_template('delete.html')

    return response


@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        try:
            verify_otp(request.form['otp'])
        except ValueError:
            return '', 400
        else:
            dynamo.tables['posts'].put_item(
                Item={
                    'id': int(time.time()),
                    'date': datetime.datetime.now().strftime("%Y-%m-%d"),
                    'title': request.form['title'].strip(),
                    'content': request.form['content']
                }
            )
            return '=)'

    else:
        return render_template('new.html')


@app.route('/health')
@app.route('/health/')
def health():
    return '=)'


def read_from_s3(bucket, key):
    client = boto3.client('s3')

    _object = client.get_object(
        Bucket=bucket,
        Key=key)

    content = _object['Body'].read()
    return content


def verify_otp(token):
    yubikey_owner = read_from_s3(
        bucket='taybird-birdnest-creds',
        key='yubikey_key_id')

    yubico_creds = read_from_s3(
        bucket='taybird-birdnest-creds',
        key='yubico').split(',')

    yubikey_client = Yubico(yubico_creds[0], yubico_creds[1])
    
    if not token[:12] == yubikey_owner:
        logging.warn('Denied unknown token: "{}"'.format(token))
        raise ValueError

    if not yubikey_client.verify(token):
        logging.warn('Token failed to validate: "{}"'.format(token))
        raise ValueError


