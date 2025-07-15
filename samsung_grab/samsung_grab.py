from argparse import ArgumentParser
from bs4 import BeautifulSoup
from lxml import etree
from os import environ
from pathlib import Path
from tinydb import TinyDB, Query
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper
import apprise
import requests

BASE_URL = 'https://data.nicolas17.xyz/samsung-grab'
SAMSUNG_URL = 'https://opensource.samsung.com/uploadSearch?searchValue='

if environ.get('SAMSUNGGRAB_DB'):
    DB_PATH = Path(environ.get('SAMSUNGGRAB_DB')).expanduser()
elif environ.get('XDG_STATE_HOME'):
    DB_PATH = Path(environ.get('XDG_STATE_HOME')).expanduser() / 'samsung-grab.json'
else:
    DB_PATH = 'samsung-grab.json'

db = TinyDB(DB_PATH)


def print_task(task):
    print(f'Task ID: {task["task_id"]}')   
    print(f'Version: {task["version"]}')
    print(f'Filename: {task["filename"]}')
    print(f'Size: {task["filesize_text"]}')
    print(f'Link: {SAMSUNG_URL + task["version"]}')


def task(args):
    try:
        while True:
            username = {'username': (None, args.username)}
            task = requests.post(url=f'{BASE_URL}/get_task', files=username).json()

            if 'task_id' in task:
                if not db.search(Query()['task_id'] == task['task_id']):
                    db.insert(task)
                print_task(task)
                if args.notify or args.notify_file:
                    apobj = apprise.Apprise()
                    if args.notify:
                        apobj.add(args.notify)
                    if args.notify_file:
                        with open(args.notify_file, 'r') as file:
                            apobj.add(file.read())
                    apobj.notify(title='samsung-grab: new task',
                                 body=SAMSUNG_URL + task['version'])
                if not args.all:
                    break
            elif 'error' in task:
                print('Message from server:')
                print(task['error'])
                break
            else:
                print('Unknown response from server:')
                print(task)
                break

    except Exception as e:
        print(e)


def upload(args):
    try:
        file = Path(args.file)
        if args.id:
            task = db.search(Query()['task_id'] == args.id)
        else:
            task = db.search(Query()['filename'] == file.name)

        if len(task) == 1:
            task = task[0]
        else:
            raise ValueError("Could not find task.\n"
                             "Try setting the task ID with '--id'.")

        data = {
            'task_id': task['task_id'],
            'file_size': file.stat().st_size,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        upload_url = requests.post(url=f'{BASE_URL}/begin_upload', data=data,
                                   headers=headers).json()
        if 'uploadURL' in upload_url:
            upload_url = upload_url['uploadURL']
        else:
            print('Message from server:')
            print(upload_url['error'])
            exit(1)

        print(f'Uploading {file.name}')
        with open(file, 'rb') as f:
            with tqdm(total=file.stat().st_size,
                      unit='B',
                      unit_scale=True,
                      unit_divisor=1024) as pbar:
                wrapped_file = CallbackIOWrapper(pbar.update, f, "read")
                upload = requests.put(url=upload_url, data=wrapped_file)
                if upload.status_code == 200:
                    data = {'task_id': task['task_id']}
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    status = requests.post(url=f'{BASE_URL}/complete_upload', data=data,
                                           headers=headers).json()['status']
                    if status == 'ok':
                        db.remove(Query()['task_id'] == task['task_id'])
                        tqdm.write('Upload finished')
                else:
                    tqdm.write('Upload failed')
                    exit(1)
    except Exception as e:
        print(e)


def list_tasks(args):
    count = 0
    if len(db) > 0:
        for i in db:
            count += 1
            print_task(i)
            if count < len(db):
                print()
    else:
        print('No tasks available')


def stats(args):
    stats = requests.get(f'{BASE_URL}/stats')
    soup = BeautifulSoup(stats.content, "html.parser")
    dom = etree.HTML(str(soup))

    pending = (dom.xpath('//*[@id="counts"]/tr[1]/td[1]')[0].text,
               dom.xpath('//*[@id="counts"]/tr[1]/td[2]')[0].text)
    claimed = (dom.xpath('//*[@id="counts"]/tr[2]/td[1]')[0].text,
               dom.xpath('//*[@id="counts"]/tr[2]/td[2]')[0].text)
    uploading = (dom.xpath('//*[@id="counts"]/tr[3]/td[1]')[0].text,
                 dom.xpath('//*[@id="counts"]/tr[3]/td[2]')[0].text)
    done = (dom.xpath('//*[@id="counts"]/tr[4]/td[1]')[0].text,
            dom.xpath('//*[@id="counts"]/tr[4]/td[2]')[0].text)

    print(f'Pending:   {pending[0]} ({pending[1]})')
    print(f'Claimed:   {claimed[0]} ({claimed[1]})')
    print(f'Uploading: {uploading[0]} ({uploading[1]})')
    print(f'Done:      {done[0]} ({done[1]})')


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    task_arg = subparsers.add_parser('task',
                                     aliases=["t"],
                                     help='Request task')
    task_arg.set_defaults(func=task)
    task_arg.add_argument('--all', '-a', action='store_true',
                          help='Request multiple tasks from server')
    task_arg.add_argument('--notify', '-n', type=str,
                          help='Apprise URL for task notifications')
    task_arg.add_argument('--notify-file', '-N', type=Path,
                          help='Path to file containing Apprise URL' +
                          ' for notifications')
    task_arg.add_argument('username', type=str,
                          help='Username for the leaderboard')

    upload_arg = subparsers.add_parser('upload',
                                       aliases=["u"],
                                       help='Upload file')
    upload_arg.set_defaults(func=upload)
    upload_arg.add_argument('file', type=Path,
                            help='File to upload')
    upload_arg.add_argument('--id', '-i', type=str,
                            help='Manually set task ID')

    list_arg = subparsers.add_parser('list',
                                     aliases=["l"],
                                     help='List claimed tasks')
    list_arg.set_defaults(func=list_tasks)

    stats_arg = subparsers.add_parser('stats',
                                     aliases=["s"],
                                      help='Query statistics')
    stats_arg.set_defaults(func=stats)

    args = parser.parse_args()
    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
        exit(1)


if __name__ == '__main__':
    main()
