from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(name="predictors", packages=find_packages(".", exclude=["tests", "scripts"]))
