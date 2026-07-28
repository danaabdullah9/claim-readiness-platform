
-- CREATE TABLE USERS (
--     user_ID INTEGER PRIMARY KEY AUTOINCREMENT,
--     name TEXT NOT NULL,
--     email TEXT NOT NULL UNIQUE,
--     phone_number TEXT,
--     password TEXT NOT NULL
-- );




-- DROP TABLE USERS;


--  CREATE TABLE USERS (
--      user_ID INTEGER PRIMARY KEY AUTOINCREMENT,
--      name TEXT ,
--      email TEXT NOT NULL UNIQUE,
--      phone_number TEXT,
--      password TEXT NOT NULL
--  );




-- INSERT INTO USERS ( email, password)
-- VALUES (
    
--     'Ghalyah@example.com',
--     'password123'
-- );



-- INSERT INTO USERS ( email, password)
-- VALUES (
    
--     'ghalyah@example.com',
  
--     'password123'
-- );







-- SELECT * FROM USERS;
INSERT INTO USERS (name, email, phone_number, password)
VALUES (
    'Dana',
    'user@bupa.com',
    '0555555555',
    '123456'
);

SELECT name
FROM sqlite_master
WHERE type = 'table';

