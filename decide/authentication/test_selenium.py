from django.test import TestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from base.tests import BaseTestCase

import time

#ponemos esta clase por problemas de compatibilidad con baseTestCase

class AdminTestCase(StaticLiveServerTestCase):

    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase() #creamos un baseTestCase para luego (next linea) llamar al metodo setUp d esa clase
        self.base.setUp() #esto nos crea un usuario q es admin, y otro q no lo es (mirarlo en base -> tests.py, el setUp ->
        #(eso es lo q estamos importando e inicializando))

        options = webdriver.ChromeOptions() #clase options, del webdriver d selenium (opciones de chrome)
        #options.headless = True #esto lanza un chrome pero de manera invisible al programador
        self.driver = webdriver.Chrome(options=options) #instancia del webdriver con esas opciones

        super().setUp()

    #Recordar q el teardown lo q hace es restaurarlo todo a como estaba
    def tearDown(self):

        super().tearDown() #llama al teardown del padre
        self.driver.quit() #cierra el navegador
        self.base.tearDown() #borra esos modelos de la bd

    def test_simpleCorrectLogin(self):

        self.driver.get(f'{self.live_server_url}/admin') #abre la next ruta del navegador -> self.live_server_url -> url del server de prueba del test
        self.driver.find_element(By.ID, 'id_username').send_keys("admin") #busca el elemento id_username y escribe admin (el id_username) 
        #lo se haciendo como en webscrapping
        
        time.sleep(3) #para q tarde + en ejecutar y ver el navegador
        self.driver.find_element(By.ID, 'id_password').send_keys("querty", Keys.ENTER) #-> dsp d poner querty en password, darle a enter-> Keys.ENTER
        time.sleep(3)

        #print(self.driver.current_url)
        #In case of a correct loging, a element with id 'user-tools' is shown in the upper right part
        #ahora mismo esta puesto el len == 0 pq la contraseña querty q se indica arriba no es la contraseña del admin y da error, y no se 
        self.assertTrue(len(self.driver.find_elements(By.ID, 'user-tools'))==0) #para verificar si hemos entrado (buscamos un elemnto con id user-tools
        # esta barra es la q t da opciones de deslogearte etc, por lo q si está (1), significa q se ha logueado correctamente)


    #con este metodo hacemos q aparezca un pop up indicando el error
    def test_simpleWrongLogin(self):
        self.driver.get(f'{self.live_server_url}/admin')
        self.driver.find_element(By.ID, 'id_username').send_keys("WRONG")
        self.driver.find_element(By.ID, 'id_password').send_keys("WRONG")
        self.driver.find_element(By.ID, 'login-form').submit()

        #In case a incorrect login, a div with class 'errornote' is shown in red!
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME, 'errornote'))==1)