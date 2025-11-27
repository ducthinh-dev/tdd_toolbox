# Tool box 

This is a module for some utilities that are made to used for database connection (MySQL, Microsoft SQL Server), image downloading, email sending and some other stuffs.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the latest version within the `dist` directory.

```bash
pip install tdd_toolbox-1.3.5.tar.gz
```

## Usage
This is sample usage for each. For more detail, please read the code.

### Connector

```python
from tools import Connector

# MySQL Connector
# Initialize
conn = Connector(
    host='10.16.x.x',
    username='username',
    password='secret_password',
    schema='database_name',
    user='auto_job' # optional, for logging purpose
)

# Refresh 
conn.refresh_connection()

# Insert 
cols = ['first_col', 'second_col']
values = [('70', 2123.3), ('80', 123)]
conn.insert(
    table='TableName',
    columns=cols,
    values=values
)

# Update
conn.update(
    table='table_name',
    conditions=[[{
                "column": column_name,
                "value": value,
                "operator": 'eq'
            }]],
    updates=[('column_name', 'update_value'),]
)

# Query
query_statement = 'select col_1, col_2 from table_name where col_3 = %s;'
columns, raw_data = conn.query_data(query=query_statement, params=['check_value',])
```
- The methods of `Connector` are using `%s` for parameter markers while the `MSSQLConnector` is using `?`.
- The condition dict is a 2-d array: the first dimension present the `or` statement and the second dimension presents the `and`. For example, the query condition `where (name = 'Thinh' and age >= 18) or (name = 'John' and age < 18)` can be presented as:
```python
[
    [
        {'column': 'name', 'operator': 'eq', 'value': 'Thinh'},
        {'column': 'age', 'operator': 'gq', 'value': 18},
    ],
    [
        {'column': 'name', 'operator': 'eq', 'value': 'John'},
        {'column': 'age', 'operator': 'lt', 'value': 18},
    ],
]
```

### Downloader
There are 2 versions of it but the `DownloaderV2` is recommended.

```python
from tools import DownloaderV2

# Initialize
downloader = DownloaderV2(store_path=Path('D:/path/to/your/directory/'))

# Download an image from an URL
await downloader.get(
    url='example.com/coolest_image.png',
    name='save_name', # optional, it will keep the original name from the url if leave blank
    is_overwritten=True, # optional, if is_overwritten set to True, it will overwrite existing image with the same name in the working directory, otherwise, raise error.
)
```

### Email Sender

```python
from tools import MailSender

# Initialize
mailer = MailSender(
    sender='email@abc.com',
    password='super_secret_password'
)

# Send an email
mailer.send_email(
    subject='Notice email',
    content='Email main content',
    content_type='HTML',
    receivers=['xxx@guardian.com.vn'],
    cc_receivers=['xxx@guardian.com.vn'],
    bcc_receivers=['xxx@guardian.com.vn'],
    attachments=[Path('D:/path/to/the/attachment/file')],
    embedded_images={'image_id': 'path/to/image'}
)
```