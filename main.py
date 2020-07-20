import asyncio

from kbs.ssc_utils.server import Server


if __name__ == "__main__":
    app = Server()
    asyncio.run(app.start_server())



# import setuptools
# import requirements

 
# install_requires = []
#
#
# with open('requirements.txt') as fd:
#     for req in requirements.parse(fd):
#         if req.name:
#             name = req.name.replace("-", "_")
#             full_line = name + "".join(
#                 ["".join(list(spec)) for spec in req.specs])
#             install_requires.append(full_line)
#
#
# setuptools.setup(
#     name="DBAccess",
#     version="0.6",
#     package_dir={"": "src"},
#     packages=setuptools.find_namespace_packages(
#         exclude=['tests'], where="src"),
#     scripts=[],
#
#     # installed and upgrade on the target machine
#     install_requires=install_requires,
#
#     # extra data for the package
#     package_data={
#         "DBAccess.config": ["*.ini", ],
#     },
#
#     # metadata to displat on PyPI
#     author="Vadim VZ. Zhdanov",
#     author_email="vz.vadia@gmail.com",
#     description="Package for database access",
#     long_description=open('README.md').read(),
#     keywords="PizzaBot DataBase Access",
#     url="https://github.com/alexkovyev/-PB.DataBaseBridge",  # project homepage
#     project_urls={
#         "Bug Tracker":
#             "https://github.com/alexkovyev/-PB.DataBaseBridge/issues",
#         "Documentation": "",
#         "Source Code": "https://github.com/alexkovyev/-PB.DataBaseBridge",
#     },
#     classifiers=[
#         "License :: OSI Approved :: Python Software Foundation License"
#     ]
# )
