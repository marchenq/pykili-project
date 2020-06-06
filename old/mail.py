''' @ TO DO:
    actions:
    +bin
    +password again
'''

import sqlite3, hashlib, binascii, os, stdiomask, time, sys
import pprint
from tabulate import tabulate
from datetime import date
from colorama import init, Fore, Back, Style

def sqlConnect():
    conn    = sqlite3.connect("mail.db", timeout=10)
    cursor  = conn.cursor()
    # conn.set_trace_callback(print) # отладка sql - запросов, в релизе уберем
    return cursor, conn


def hashPassword(password):
    salt    = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii') # генеририуем соль (штука, которая передается хэш-функции вместе с паролем, чтобы одинаковые пароли в бд были представлены по-разному)
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def register():
    cursor, conn = sqlConnect()
    
    username = input('\nEnter your username' + Fore.RED + '*' + Style.RESET_ALL + ': ')

    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, ))
    userId = cursor.fetchall()

    if len(userId) != 0:
        print(Fore.CYAN + '\nThis user already exists. Please choose another username')
        register()
    else:        
        password    = input('Enter your password' + Fore.RED + '*' + Style.RESET_ALL + ': ')
        hashedPwd   = hashPassword(password)
        name        = input('Enter your name' + Fore.RED + '*' + Style.RESET_ALL + ': ')
     #   status      = input('Enter your status (teacher, student): ')

        if username != '' and password != '':
            query = '''
             INSERT INTO users
                 (username, password, name)
             VALUES
                  (?,?,?)
                '''
            data = (username, hashedPwd, name)
            cursor.execute(query, data)
            conn.commit()
            print(Fore.CYAN + '\nNice to meet you, ' + name + '! You have been successfuly registered with the following details: ' + username + ':' + password + '.\nYou can now sign in.')
            auth()
        else:
            print(Fore.CYAN + '\nNor username neither password can be empty!')
            register()


def verifyPassword(storedPassword, providedPassword): # функция проверки введенного пароля на соответствие зашифрованному в бд
    salt = storedPassword[:64]
    storedPassword = storedPassword[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512', 
                                  providedPassword.encode('utf-8'), 
                                  salt.encode('ascii'), 
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == storedPassword


def auth():
    cursor, conn = sqlConnect()
    
    username = input('\nEnter your username: ')
    password = stdiomask.getpass(prompt='Enter your password: ')

    cursor.execute("SELECT user_id, password, name FROM users WHERE username = ?", (username, )) # проверяем наличие аккаунта в базе
    userInfo = cursor.fetchone()

    if str(userInfo) != 'None':
        userId    = str(userInfo[0])
        storedPwd = str(userInfo[1])
        name      = str(userInfo[2])
           
        if verifyPassword(storedPwd, password) == True:
            print(Fore.CYAN + Style.BRIGHT + '\nWelcome back, '+ name + '!')
            actionChoice(userId)
        else:
            print(Fore.WHITE + Back.RED + 'Wrong details!')
            auth()
    else:
        choice = input('\nThere is no such account! Want to create one? (y\\n): ')
        if choice == 'y':
            register()
        if choice == 'n':
            auth()
        if choice == '0':
            quitf()
        else:
            print('Invalid choice!')
            quitf()
            


def actionChoice(userId):
    print(tabulate([['1','View Inbox'],['2','View Outbox'],['3','Send a letter']], ["#", "Action"], tablefmt="fancy_grid"))
    action = input('What would you like to do? Choose a number: ')
    if action == '1':
        getLetters(userId)
    elif action == '2':
        viewOutbox(userId)
    elif action == '3':
        sendLetter(userId, None)
    elif action ==  '0':
        quitf()
    else:
        print(Style.BRIGHT + Fore.RED + 'Invalid choice!')
        actionChoice(userId)
    

def viewOutbox(userId):
    cursor, conn = sqlConnect()
    
    cursor.execute('''
                    SELECT
                        letters.id, users.name, letters.date, letters.theme
                    FROM
                        letters, users
                    WHERE
                        sender_id = ?
                    AND
                        users.user_id = letters.sender_id
                    ORDER BY
                        id
                    DESC
                    ''', (userId,))
    
    results = cursor.fetchall()
    print(tabulate(results, headers=['№', 'Sent To', 'Date', 'Theme'], tablefmt='fancy_grid'))
    
    letterId = input('Which letter do you want to read?: ')
    if letterId == '0':
        quitf()

    cursor.execute('''
                SELECT
                    sender_id
                FROM
                    letters
                WHERE
                    id = ?
                    ''', (letterId, ))

    sender_id = cursor.fetchone()[0]

    if int(sender_id) == int(userId):
        cursor.execute('''
                    SELECT
                        letters.data, letters.date, letters.theme, sender_id
                    FROM
                        letters 
                    WHERE
                        id = ?
                    ''', (letterId, ))
        letter = cursor.fetchone()
        letterData  = str(letter[0])
        letterDate  = str(letter[1])
        letterTheme = str(letter[2])
        sender_id   = str(letter[3])
        
        print('\n==================================================')
        print('Date: '    + Style.DIM                  + letterDate)
        print('To: '      + Style.BRIGHT + Fore.YELLOW + letterTheme) 
        print('Subject: ' + Style.BRIGHT + Fore.YELLOW + letterTheme)
        print('\n'        + Style.BRIGHT               + letterData + '\n')
        print('==================================================')
        actionChoice(userId)
    else:
        print(Fore.RED + 'Do not read other people\'s letters!')
        viewOutbox(userId)


def getLetters(userId):
    cursor, conn = sqlConnect()
    
    cursor.execute('''
                    SELECT
                        letters.id, users.name, letters.date, letters.theme, letters.read
                    FROM
                        letters, users
                    WHERE
                        receiver_id = ?
                    AND
                        users.user_id = letters.sender_id
                    ORDER BY
                        id
                    DESC
                    ''', (userId,))
    
    results = cursor.fetchall()
    updatedRes = []
    
    for element in results:
        element = list(element)
        updatedRes.append(element)
        
    for element in updatedRes:
        element[4] = str(element[4])
        if element[4] == '0':
            element[1] = Fore.CYAN + Style.BRIGHT + element[1] + Style.RESET_ALL
            element[2] = Fore.CYAN + Style.BRIGHT + element[2] + Style.RESET_ALL
            element[3] = Fore.CYAN + Style.BRIGHT + element[3] + Style.RESET_ALL
        del element[4]
    
    print('\n This is your inbox folder:')
    print(tabulate(updatedRes, headers=['№', 'Sent By', 'Date', 'Theme'], tablefmt='fancy_grid'))

    letterId = input('Which letter do you want to read? ')
    if letterId ==  '0':
        quitf()

    cursor.execute('''
                SELECT
                    receiver_id
                FROM
                    letters
                WHERE
                    id = ?
                    ''', (letterId, ))

    receiver_id = cursor.fetchone()
    
    if receiver_id == None:
        print(Fore.RED + 'Do not read other people\'s letters!')
    else:
        if int(receiver_id[0]) == int(userId):
            cursor.execute('''
                        SELECT
                            letters.data, letters.date, letters.theme, sender_id
                        FROM
                            letters
                        WHERE
                            id = ?
                        ''', (letterId, ))
            letter = cursor.fetchone()
            letterData  = str(letter[0])
            letterDate  = str(letter[1])
            letterTheme = str(letter[2])
            sender_id   = str(letter[3])

            cursor.execute('''
                    UPDATE
                        letters
                    SET
                        read = '1'
                    WHERE
                        id = ?
                    ''', (letterId))
                           
            conn.commit()
            
            cursor.execute('''
                        SELECT
                            name
                        FROM
                            users
                        WHERE
                            user_id = ?
                        ''', (sender_id, ))

            letterFrom = cursor.fetchone()

            print('\n==================================================')
            print('Date: '    + Style.DIM                  + letterDate)
            print('From: '                                 + letterFrom[0])
            print('Subject: ' + Style.BRIGHT + Fore.YELLOW + letterTheme)
            
            print('\n' + Style.BRIGHT + letterData + '\n')
            print('==================================================')
            choice = input('\nWant to reply?')
            if choice == 'y':
                cursor.execute ('''
                        SELECT
                            sender_id
                        FROM
                            letters
                        WHERE
                            id = ? ''', (letterId))
                senderId = cursor.fetchone()[0]
                sendLetter(userId, senderId)
            if choice == '0':
                quitf()
            else:
                actionChoice(userId)
        else:
            print(Fore.RED + 'Do not read other people\'s letters!')
            getLetters(userId)


def sendLetter(userId, receiverId):
    cursor, conn = sqlConnect()

    recvList = []

    if receiverId == None:
        receiver = input('Who do you want to send a letter to? (type \'list\' to see users list): ')
        if receiver == 'list':
            cursor.execute ('''
                            SELECT
                                username, name, status
                            FROM
                                users
                            ''')
            
            usersList = cursor.fetchall()
            print(tabulate(usersList, headers=['Username', 'Name', 'Status'], tablefmt='fancy_grid'))     
            sendLetter(userId, receiverId)
        else:
            receiver = receiver.replace(' ', '')
            receiversList = receiver.split(',')

        for recv in receiversList:
            cursor.execute('''
                            SELECT
                                user_id
                            FROM
                                users
                             WHERE
                                username = ?
                            ''', (recv,))
            receiverId = str(cursor.fetchone())
            receiverId = receiverId.replace(',','')
            receiverId = receiverId.replace('(','')
            receiverId = receiverId.replace(')','')

            if receiverId == 'None':
                print('There is no user', recv)
                sendLetter(userId, None)
            else:
                recvList.append(receiverId)
    else:
        recvList.append(receiverId)

    if len(recvList) != 0:
        theme  = input('Enter letter topic: ') 
        letter = input('Write your letter: ')
        letterDate = date.today().strftime('%B %d %H:%M')
        choice = input('Please confirm sending this letter (y\\n): ')

        if choice == 'y':
            for receiverId in recvList:
                query = '''
                        INSERT INTO letters
                            (sender_id, receiver_id, date, theme, data)
                        VALUES
                            (?,?,?,?,?)
                        '''
                data = (userId, receiverId, letterDate, theme, letter)
                cursor.execute(query,data)
                conn.commit()
                print(Fore.GREEN + 'You have successfully sent the letter.')
                actionChoice(userId)
        else:
            print(Fore.CYAN + 'Sending has been cancelled.')
            actionChoice(userId)
    else:
        actionChoice(userId)


def main():
    init(autoreset = True) # для colorama

    os.system('title Console E-mail Client v.0.1')
    
    print(Back.BLUE + Style.BRIGHT + '+-+-+-+-+-+-+-+ +-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+'.center(120, ' '), end='')
    print(Back.BLUE + Style.BRIGHT + '|C|o|n|s|o|l|e| |M|e|s|s|e|n|g|e|r| |v|.|0|.|1|'.center(120, ' '), end='')
    print(Back.BLUE + Style.BRIGHT + '+-+-+-+-+-+-+-+ +-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+'.center(120, ' '), end='')
    print(Style.BRIGHT + Fore.YELLOW + 'Welcome! ' + Style.RESET_ALL + '\n(You can close the app at any time by entering 0)')

    action = input('\nWhat would you like to do? (1 - Login, 2 - Register): ')
    if action == '1':
        auth()
    elif action == '2':
        register()
    if action == '0':
        quitf()
    else:
        print('Invalid choice!')

def quitf():
    print('Good bye! Closing the app in 5 seconds...')
    time.sleep(5)
    
if __name__ == "__main__":
    main()
