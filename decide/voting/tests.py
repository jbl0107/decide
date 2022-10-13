import random
import itertools
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from base import mods
from base.tests import BaseTestCase
from census.models import Census
from mixnet.mixcrypt import ElGamal
from mixnet.mixcrypt import MixCrypt
from mixnet.models import Auth
from voting.models import Voting, Question, QuestionOption

#Para q sea una prueba tiene q heredar de BaseTestCase
class VotingModelTC(BaseTestCase):

    #genera una pregunta con 2 opciones y una votacion con esa pregunta, y la almacena dentro del modelo d django
    def setUp(self):
        q = Question(desc="Descripcion") #creamos y guardamos una pregunta
        q.save()

        opt1 = QuestionOption(question=q, option="option1") #creamos y guardamos 2 opciones pertenecientes a la pregunta creada
        opt1.save()

        opt2 = QuestionOption(question=q, option="option2")
        opt2.save()

        self.v = Voting(name='Votacion', question = q)
        self.v.save()

        #llamar al setUp d la clase padre (esto hacerlo siempre) para evitar problemas)
        super().setUp()


    def tearDown(self):
        return super().tearDown()
        self.v = None #lo q hemos hecho (entiendo q en el setUp) ha sido crear un objeto de tipo votacion en la clase, lo deshacemos asi

    #Este es nuestro metodo, q va a rescatar el objeto del modelo y ver si se guarda (prueba de tipo CRUD) (son pruebas del unitarias)
    def testExist(self):
        #podemos rescatar esa votacion con por ej el nombre
        v = Voting.objects.get(name = 'Votacion')
        #comprobamos si la votacion q me acabo de traer, de entre todas sus opciones (options.all devuelve un array), la 1ra, es option1 (linea 28)
        #si cambiamos a option2, debe de fallar, ya q la opcion 1 de todas las opciones de la votacion, segun como
        #hemos puesto en el setUp, es 'option1', o si no nuestro metodo de guardar una votacion no funciona. Si pongo [2] y de texto 'option2', debe
        #funcionar correctamente, ya q la 2da opcion (tal y como hemos definido en el setup es 'option2')
        self.assertEquals(v.question.options.all()[0].option, "option1")
        '''podemos mejorar esta prueba, por ej, añadiendo:
            self.assertEquals(v.question.options.all()[1].option, "option2")
            self.assertEquals(len(v.question.options.all()), 2) -> el nº de opciones de la votacion sea 2
        '''

    def testCreatingVotingAPI(self):
        self.login() #conseguimos q se haga la peticion al login
        #creamos unos datos para poder realizar dsp la peticion con estos (en formato json, ya q es una api)
        data = {
            'name':'Example',
            'desc':'Description',
            'question':'I wanna',
            'question_opt':['car', 'house', 'party'] #posibles opciones a la pregunta
        }

        
        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code,201) #verificar q esa peticion se realiza bn

        #Aqui verificamos q, la votacion obtenida en v, tiene la misma descripcion q la creada en data
        v = Voting.objects.get(name = 'Example')
        self.assertEqual(v.desc,'Description')


class VotingTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    
    #en este test se utiliza el tostring (__str__) de la votacion(voting), de la pregunta y de las opciones, q son 3 de las 4 lineas q no estabamos probando
    # q se indicaban en el coverage (en la parte de model/voting) (mirar si no el video de la practica 2 q dura 1:43:08) 
    #si no recuerdo bn, quitar este metodo, generar el coverage, mirar el model/voting y ver lo q no se cubre, poner este test, regenerar el coverage y ver
    #la diferencia, como ya se cubren 3 de las 4 lineas q no lo estaban
    def test_Voting_toString(self):
        v = self.create_voting() #crea votaciones y las almacena
        self.assertEquals(str(v),"test voting") #llama al tostring y ya dsp verifica
        self.assertEquals(str(v.question),"test question")  
        self.assertEquals(str(v.question.options.all()[0]),"option 1 (2)")


    def encrypt_msg(self, msg, v, bits=settings.KEYBITS):
        pk = v.pub_key
        p, g, y = (pk.p, pk.g, pk.y)
        k = MixCrypt(bits=bits)
        k.k = ElGamal.construct((p, g, y))
        return k.encrypt(msg)

    def create_voting(self):
        q = Question(desc='test question')
        q.save()
        for i in range(5):
            opt = QuestionOption(question=q, option='option {}'.format(i+1))
            opt.save()
        v = Voting(name='test voting', question=q)
        v.save()

        a, _ = Auth.objects.get_or_create(url=settings.BASEURL,
                                          defaults={'me': True, 'name': 'test auth'})
        a.save()
        v.auths.add(a)

        return v

    def create_voters(self, v):
        for i in range(100):
            u, _ = User.objects.get_or_create(username='testvoter{}'.format(i))
            u.is_active = True
            u.save()
            c = Census(voter_id=u.id, voting_id=v.id)
            c.save()

    def get_or_create_user(self, pk):
        user, _ = User.objects.get_or_create(pk=pk)
        user.username = 'user{}'.format(pk)
        user.set_password('qwerty')
        user.save()
        return user

    def store_votes(self, v):
        voters = list(Census.objects.filter(voting_id=v.id))
        voter = voters.pop()

        clear = {}
        for opt in v.question.options.all():
            clear[opt.number] = 0
            for i in range(random.randint(0, 5)):
                a, b = self.encrypt_msg(opt.number, v)
                data = {
                    'voting': v.id,
                    'voter': voter.voter_id,
                    'vote': { 'a': a, 'b': b },
                }
                clear[opt.number] += 1
                user = self.get_or_create_user(voter.voter_id)
                self.login(user=user.username)
                voter = voters.pop()
                mods.post('store', json=data)
        return clear

    def test_complete_voting(self):
        v = self.create_voting()
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}

        for q in v.question.options.all():
            self.assertEqual(tally.get(q.number, 0), clear.get(q.number, 0))

        for q in v.postproc:
            self.assertEqual(tally.get(q["number"], 0), q["votes"])

    def test_create_voting_from_api(self):
        data = {'name': 'Example'}
        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = mods.post('voting', params=data, response=True)
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        response = mods.post('voting', params=data, response=True)
        self.assertEqual(response.status_code, 400)

        data = {
            'name': 'Example',
            'desc': 'Description example',
            'question': 'I want a ',
            'question_opt': ['cat', 'dog', 'horse']
        }

        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 201)

    def test_update_voting(self):
        voting = self.create_voting()

        data = {'action': 'start'}
        #response = self.client.post('/voting/{}/'.format(voting.pk), data, format='json')
        #self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        data = {'action': 'bad'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)

        # STATUS VOTING: not started
        for action in ['stop', 'tally']:
            data = {'action': action}
            response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), 'Voting is not started')

        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting started')

        # STATUS VOTING: started
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting is not stopped')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting stopped')

        # STATUS VOTING: stopped
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting tallied')

        # STATUS VOTING: tallied
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already tallied')
