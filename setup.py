from setuptools import setup, find_packages

setup(
    name="hypercode",
    version="0.1.0",
    packages=find_packages(where="."),
    package_dir={"": "."},
    install_requires=[
        "antlr4-python3-runtime>=4.13",
        "pydantic>=2.0",
        "qiskit>=0.44.0",
        "qiskit-aer>=0.13",
        "typing-extensions>=4.0"
    ],
    python_requires=">=3.10",
    entry_points={
        'console_scripts': [
            'hypercode=hypercode.cli:main',
        ],
    },
)
