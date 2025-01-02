CREATE DATABASE IF NOT EXISTS bnb_database;
USE bnb_database;

CREATE TABLE rooms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,  
    description TEXT,
    price_per_night DECIMAL(10,2) NOT NULL,
    capacity INT NOT NULL,
    image_url VARCHAR(255),
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bookings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    room_id INT NOT NULL,
    guest_name VARCHAR(100) NOT NULL,
    guest_email VARCHAR(100) NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

INSERT INTO rooms (name, description, price_per_night, capacity) VALUES
('Leonardo da Vinci', 'Elegante camera con vista sul giardino, ispirata al genio del Rinascimento', 120.00, 2),
('Michelangelo', 'Spaziosa suite con affreschi e decorazioni rinascimentali', 150.00, 3),
('Raffaello', 'Camera romantica con balcone privato', 130.00, 2),
('Caravaggio', 'Suite drammatica con illuminazione particolare e arredo barocco', 140.00, 2),
('Botticelli', 'Camera delicata con tema primaverile e vista panoramica', 135.00, 2);

ALTER TABLE bookings ADD COLUMN guests INT NOT NULL DEFAULT 1;

ALTER TABLE bookings ADD COLUMN confirmation_code VARCHAR(10) UNIQUE;

