# AraGeno
AraGeno is a django web-application for allowing researchers to easily run [SNPmatch](https://github.com/Gregor-Mendel-Institute/SNPmatch) 
using the web-browser. The user only needs to upload a VCF or BED file. The analysis will be run on a HPC that needs to be configured seperately. 

## Installation & Usage

The below steps only deal with the web-application part. In order to run AraGeno, also SNPmatch must be installed on a HPC and configured properly

### Using pip: 

```bash
git clone git@github.com:Gregor-Mendel-Institute/AraGeno.git 
cd AraGeno
pip install -r requirements.txt
```
Run the django web-app: 

```BASH
./manage runserver
```

Run the listener for the HPC jobs:

```bash
./manage.py listen_job_queue 'amqp://AMQP_BROKER'
```

### Using docker/docker-compose:

Create .env file for environment variables:

```
EMAIL_HOST=[EMAIL_HOST]
EMAIL_USER=[EMAIL_USER]
BROKER=[AMQP BROKER FOR JOB INFOS]
HPC_USER=[HPC_USER]
ALLOWED_HOSTS=[ALLOWED_HOSTS]
SECRET_KEY=[SECRET]
```
Checkout code and ruin docker-compose:

```bash
git clone git@github.com:Gregor-Mendel-Institute/AraGeno.git 
cd AraGeno
docker-compose up -d 
```


## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D


## History

- 0.0.1: Initial implementation


## Credits

- Ümit Seren (uemit.seren[at]gmi.oeaw.ac.at)
- Rahul Pisupati (rahul.pisupati[at]gmi.oeaw.ac.at)
- Ilka Reichardt-Gomez (ilka.reichardt[at]gmi.oeaw.ac.at)
- Envel Kerdaffrec (envel.kerdaffrec[at]gmi.oeaw.ac.at)


## License
MIT license
