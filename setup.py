from setuptools import setup, find_packages

setup(
    name="newananas",  # Изменено с "rlofc" на "newananas"
    version="1.0.0",
    description="Reinforcement Learning for Open Face Chinese Poker",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(exclude=["tests*"]),  # Исключаем тесты из установки
    include_package_data=True,  # Включаем неисполняемые файлы (templates, static)
    package_data={
        'web': ['templates/*', 'static/*'],  # Указываем файлы для включения
    },
    install_requires=[
        "numpy>=1.19.0",
        "tensorflow>=2.4.0",
        "keras>=2.4.0",
        "flask>=2.0.0",
        "matplotlib>=3.3.0",
        "seaborn>=0.11.0",
        "pyyaml>=5.4.0",
        "deuces>=0.2.0",
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
    python_requires='>=3.8',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        'console_scripts': [
            'newananas-web=web.app:main',  # Добавляем точку входа для веб-приложения
        ],
    },
)
