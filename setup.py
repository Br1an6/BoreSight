from setuptools import setup, find_packages

setup(
    name='boresight',
    version='0.1.0',
    packages=find_packages(),
    py_modules=['main'],
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "httpx>=0.24.0",
        "langchain>=0.2.0",
        "langchain-community>=0.2.0",
        "langchain-ollama>=0.1.0",
        "langchain-openai>=0.1.0",
        "langchain-anthropic>=0.1.0",
        "langchain-google-genai>=1.0.0",
        "langgraph>=0.0.10",
        "click>=8.0.0",
        "pydantic>=2.0.0",
        "scipy>=1.10.0",
        "scikit-learn>=1.2.0",
        "networkx>=3.0"
    ],
    entry_points={
        'console_scripts': [
            'boresight=main:cli',
        ],
    },
)
