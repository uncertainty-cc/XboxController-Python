import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cc.xboxcontroller",
    version="2023.12.26",
    author="Uncertainty.",
    author_email="t_k_233@outlook.email",
    description="Getting input from Microsoft XBox 360 controllers via the XInput library on Windows.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/uncertainty-cc/XboxController-Python",
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
    python_requires=">=3.8",
)
