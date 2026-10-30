-- ==========================================================================
-- Karnataka Explore - MySQL 8 schema
-- Create the database first, then run this file:
--   CREATE DATABASE karnataka_explore CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--   mysql -u root -p karnataka_explore < schema/mysql_schema.sql
-- Set DB_BACKEND=mysql and the DB_* variables in .env to use it.
-- ==========================================================================

CREATE TABLE IF NOT EXISTS districts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  slug VARCHAR(80) NOT NULL UNIQUE,
  region VARCHAR(60),
  description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  mobile VARCHAR(15) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  district VARCHAR(80),
  gender VARCHAR(30),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL DEFAULT 'admin',
  last_login DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS destinations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  slug VARCHAR(180) NOT NULL UNIQUE,
  district_id INT NOT NULL,
  category VARCHAR(60) NOT NULL,
  description TEXT NOT NULL,
  description_hi TEXT,
  description_kn TEXT,
  location VARCHAR(200),
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  best_time VARCHAR(120),
  entry_fee VARCHAR(160),
  timings VARCHAR(160),
  activities TEXT,
  nearby TEXT,
  travel_info TEXT,
  duration VARCHAR(60),
  ticket_price DECIMAL(10,2) NOT NULL DEFAULT 0,
  featured TINYINT(1) NOT NULL DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_dest_district FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE CASCADE,
  INDEX idx_dest_district (district_id),
  INDEX idx_dest_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS destination_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  destination_id INT NOT NULL,
  image_url VARCHAR(500) NOT NULL,
  caption VARCHAR(200),
  sort_order INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_di_dest FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS homestays (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  slug VARCHAR(180) NOT NULL UNIQUE,
  district_id INT NOT NULL,
  description TEXT NOT NULL,
  address VARCHAR(300),
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  price_per_night DECIMAL(10,2) NOT NULL DEFAULT 0,
  rooms_available INT NOT NULL DEFAULT 1,
  max_guests INT NOT NULL DEFAULT 2,
  checkin_time VARCHAR(20) DEFAULT '12:00 PM',
  checkout_time VARCHAR(20) DEFAULT '11:00 AM',
  facilities VARCHAR(400),
  contact_name VARCHAR(120),
  contact_phone VARCHAR(30),
  contact_email VARCHAR(160),
  rating DECIMAL(3,1) DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  is_sample TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_hs_district FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS homestay_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  homestay_id INT NOT NULL,
  image_url VARCHAR(500) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_hi_hs FOREIGN KEY (homestay_id) REFERENCES homestays(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  homestay_id INT NOT NULL,
  room_type VARCHAR(120) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  capacity INT NOT NULL DEFAULT 2,
  total_rooms INT NOT NULL DEFAULT 1,
  CONSTRAINT fk_room_hs FOREIGN KEY (homestay_id) REFERENCES homestays(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tour_guides (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  district_id INT NULL,
  languages VARCHAR(200),
  experience INT DEFAULT 0,
  fee_per_day DECIMAL(10,2) NOT NULL DEFAULT 0,
  phone VARCHAR(30),
  email VARCHAR(160),
  bio TEXT,
  photo_url VARCHAR(500),
  rating DECIMAL(3,1) DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  is_sample TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_guide_district FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_ref VARCHAR(20) NOT NULL UNIQUE,
  user_id INT NOT NULL,
  kind ENUM('destination','homestay','guide') NOT NULL,
  destination_id INT NULL,
  homestay_id INT NULL,
  guide_id INT NULL,
  visit_date DATE NULL,
  checkin_date DATE NULL,
  checkout_date DATE NULL,
  nights INT DEFAULT 0,
  visitors INT NOT NULL DEFAULT 1,
  rooms INT DEFAULT 1,
  unit_price DECIMAL(10,2) NOT NULL DEFAULT 0,
  subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
  tax DECIMAL(10,2) NOT NULL DEFAULT 0,
  total DECIMAL(10,2) NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'Pending',
  payment_status VARCHAR(20) NOT NULL DEFAULT 'Unpaid',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_book_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_book_dest FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE SET NULL,
  CONSTRAINT fk_book_hs FOREIGN KEY (homestay_id) REFERENCES homestays(id) ON DELETE SET NULL,
  CONSTRAINT fk_book_guide FOREIGN KEY (guide_id) REFERENCES tour_guides(id) ON DELETE SET NULL,
  INDEX idx_book_user (user_id),
  INDEX idx_book_ref (booking_ref)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS booking_tickets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  ticket_no VARCHAR(40) NOT NULL,
  issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  download_count INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_ticket_book FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  method VARCHAR(40) NOT NULL,
  txn_id VARCHAR(40) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pay_book FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS guide_bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guide_id INT NOT NULL,
  booking_id INT NOT NULL,
  days INT NOT NULL DEFAULT 1,
  start_date DATE,
  CONSTRAINT fk_gb_guide FOREIGN KEY (guide_id) REFERENCES tour_guides(id) ON DELETE CASCADE,
  CONSTRAINT fk_gb_book FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  destination_id INT NULL,
  homestay_id INT NULL,
  rating INT NOT NULL,
  comment TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'Pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_rev_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_rev_dest FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE,
  CONSTRAINT fk_rev_hs FOREIGN KEY (homestay_id) REFERENCES homestays(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wishlist (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  kind VARCHAR(20) NOT NULL,
  item_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_wish (user_id, kind, item_id),
  CONSTRAINT fk_wish_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS languages (
  code VARCHAR(5) PRIMARY KEY,
  name VARCHAR(40) NOT NULL,
  native VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS contact_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL,
  phone VARCHAR(30),
  subject VARCHAR(200),
  message TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'New',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS newsletter (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(160) NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS site_content (
  `key` VARCHAR(60) PRIMARY KEY,
  value TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
