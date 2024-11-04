from setuptools import setup, find_packages

setup(
    name="newananas",
    version="1.0.0",
    description="Reinforcement Learning for Open Face Chinese Poker",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    package_data={
        'web': ['templates/*', 'static/*'],
    },
    install_requires=[
        "flask>=2.0.1",
        "flask-cors>=3.0.10",
        "werkzeug>=2.0.3",
        "gunicorn>=20.1.0",
        "numpy>=1.19.5",
        "tensorflow-cpu>=2.5.0",  # Используем CPU версию
        "torch>=1.7.1",
        "seaborn>=0.11.2",
        "matplotlib>=3.3.4",
        "pyyaml>=5.4.1",
        "requests>=2.25.1",
        "python-dotenv>=0.19.0",
        "prometheus-client>=0.17.1",
        "flask-socketio>=5.0.1",
    ],
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-cov>=2.10.0',
            'flake8>=3.8.0',
            'black>=20.8b1',
            'isort>=5.6.0',
            'mypy>=0.790',
        ]
    },
    python_requires='>=3.9',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        'console_scripts': [
            'newananas-web=web.app:main',
        ],
    },
)
