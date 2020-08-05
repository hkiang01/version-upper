import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="version-upper",  # Replace with your own username
    version="0.2.0",
    author="Harrison Kiang",
    author_email="hkiang01@gmail.com",
    description="Bump version strings in your repo",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hkiang01/version_upper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: English",
    ],
    py_modules=["version_upper"],
    python_requires=">=3.6",
    install_requires=["click>=0.7,!=3.0,!=5.0", "pydantic>=1.0b1"],
    entry_points="""
        [console_scripts]
        version-upper=version_upper:cli
    """,
)
