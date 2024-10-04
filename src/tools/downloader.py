import aiohttp
import os
import shutil


class Downloader:
    def __init__(self, store_path: str) -> None:
        self.change_storage(store_path=store_path)

    def change_storage(self, store_path: str) -> None:
        store_path = store_path if store_path[-1] == '/' else store_path + '/'
        self.storage = store_path

    async def get(self, url: str, name: str = None, is_overwritten: bool = False):
        file_ext = url.split('.')[-1]
        file_name = f'{name}.{file_ext}' if name else url.split('/')[-1]
        file_path = f'{self.storage}{file_name}'

        if os.path.isfile(file_path) and is_overwritten:
            shutil.rmtree(file_path)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.content.read()
                with open(file_path, mode='wb') as file:
                    file.write(content)
        return 1
