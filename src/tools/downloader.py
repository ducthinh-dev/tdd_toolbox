import aiohttp
import os


class Downloader:
    '''
    Class for downloading files from URLs and storing them locally.
    '''

    def __init__(self, store_path: str) -> None:
        self.change_storage(store_path=store_path)

    def change_storage(self, store_path: str) -> None:
        '''
        Change the storage path for downloaded files.

        #### Parameters:
        - store_path (str): The new storage path for downloaded files.
        '''
        store_path = store_path if store_path[-1] == '/' else store_path + '/'
        self.storage = store_path
        if not os.path.exists(self.storage):
            os.mkdir(self.storage)

    async def get(self, url: str, name: str = None, is_overwritten: bool = False):
        '''
        Download a file from a URL and save it locally.

        #### Parameters:
        - url (str): The URL of the file to download.
        - name (str, optional): The name to save the file as. If not provided, the file will be saved with its original name.
        - is_overwritten (bool, optional): If True, overwrite the file if it already exists locally.

        #### Returns:
        - str: The file path where the downloaded file is saved.
        '''
        file_ext = url.split('.')[-1]
        file_name = f'{name}.{file_ext}' if name else url.split('/')[-1]
        file_path = f'{self.storage}{file_name}'

        if os.path.isfile(file_path) and not is_overwritten:
            raise FileExistsError(f'File name ({file_name}) already exists.')

        if os.path.isfile(file_path) and is_overwritten:
            os.remove(file_path)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.content.read()
                with open(file_path, mode='wb') as file:
                    file.write(content)
        return file_path
