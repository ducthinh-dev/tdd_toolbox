from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='tdd-toolbox',
    version='0.8.2.0',
    packages=find_packages(exclude=['tests*']),
    license='MIT',
    description='Duc Thinh\'s essential tools for projects',
    long_description=open('README.txt').read(),
    install_requires=requirements,
    url='https://github.com/ducthinh-dev/tdd_toolbox',
    author='Thinh Do Duc',
    author_email='dothinh.dev@gmail.com'
)
