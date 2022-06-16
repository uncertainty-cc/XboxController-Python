import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dotxboxcontroller",
    version="0.0.1",
    author="Rath Robotics",
    author_email="tk@uncertainty.email",
    description="Getting input from Microsoft XBox 360 controllers via the XInput library on Windows.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/uncertainty-cc/dotXboxController",
    project_urls={
        
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "pyglet",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
