CREATE DATABASE  IF NOT EXISTS `db_tt` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `db_tt`;
-- MySQL dump 10.13  Distrib 9.3.0, for Win64 (x86_64)
--
-- Host: localhost    Database: db_tt
-- ------------------------------------------------------
-- Server version	9.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `area`
--

DROP TABLE IF EXISTS `area`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `area` (
  `CodigoArea` int NOT NULL AUTO_INCREMENT,
  `NombreArea` varchar(100) NOT NULL,
  `RFCEncargado` varchar(13) NOT NULL,
  PRIMARY KEY (`CodigoArea`),
  KEY `RFCEncargado` (`RFCEncargado`),
  CONSTRAINT `area_ibfk_1` FOREIGN KEY (`RFCEncargado`) REFERENCES `encargado` (`RFCEncargado`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `area`
--

LOCK TABLES `area` WRITE;
/*!40000 ALTER TABLE `area` DISABLE KEYS */;
INSERT INTO `area` VALUES (10,'Electrónica','LORM750404DD4'),(20,'Ropa y Accesorios','ROGE800505EE5'),(30,'Hogar y Jardín','SAVA880115FF6'),(40,'Juguetería','HERL920320GG7'),(50,'Deportes','MART850625HH8');
/*!40000 ALTER TABLE `area` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cliente`
--

DROP TABLE IF EXISTS `cliente`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cliente` (
  `idCliente` int NOT NULL AUTO_INCREMENT,
  `RFCCliente` varchar(13) NOT NULL,
  `Direccion` varchar(200) DEFAULT NULL,
  `TelefonoCliente` varchar(20) DEFAULT NULL,
  `CorreoCliente` varchar(80) DEFAULT NULL,
  PRIMARY KEY (`idCliente`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cliente`
--

LOCK TABLES `cliente` WRITE;
/*!40000 ALTER TABLE `cliente` DISABLE KEYS */;
INSERT INTO `cliente` VALUES (1,'GOPJ850101AA1','Calle Falsa 123, Col Centro','5512345678','juan.perez@email.com'),(2,'GAML880202BB2','Av. Siempre Viva 742','5587654321','ana.garcia@email.com'),(3,'SARM900303CC3','Blvd. de los Sueños 45','5555555555','miguel.sanchez@email.com');
/*!40000 ALTER TABLE `cliente` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `descuento`
--

DROP TABLE IF EXISTS `descuento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `descuento` (
  `idDescuento` int NOT NULL AUTO_INCREMENT,
  `Valor` decimal(10,2) NOT NULL,
  `Tipo` enum('Porcentaje','MontoFijo') NOT NULL,
  `FechaInicio` date NOT NULL,
  `FechaFin` date NOT NULL,
  `Estado` enum('Activo','Inactivo') NOT NULL,
  PRIMARY KEY (`idDescuento`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `descuento`
--

LOCK TABLES `descuento` WRITE;
/*!40000 ALTER TABLE `descuento` DISABLE KEYS */;
INSERT INTO `descuento` VALUES (1,15.00,'Porcentaje','2025-10-01','2025-10-31','Activo'),(2,50.00,'MontoFijo','2025-10-15','2025-10-25','Activo'),(3,10.00,'Porcentaje','2025-09-01','2025-09-30','Inactivo');
/*!40000 ALTER TABLE `descuento` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `encargado`
--

DROP TABLE IF EXISTS `encargado`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `encargado` (
  `RFCEncargado` varchar(13) NOT NULL,
  `NombreEncargado` varchar(80) NOT NULL,
  `ApPaterno` varchar(50) NOT NULL,
  `ApMaterno` varchar(50) DEFAULT NULL,
  `Telefono` varchar(15) DEFAULT NULL,
  `Correo` varchar(80) DEFAULT NULL,
  `idTurno` int NOT NULL,
  PRIMARY KEY (`RFCEncargado`),
  KEY `idTurno` (`idTurno`),
  CONSTRAINT `encargado_ibfk_1` FOREIGN KEY (`idTurno`) REFERENCES `turno` (`idTurno`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `encargado`
--

LOCK TABLES `encargado` WRITE;
/*!40000 ALTER TABLE `encargado` DISABLE KEYS */;
INSERT INTO `encargado` VALUES ('HERL920320GG7','Luis','Hernandez','Lopez','5544556677','luis.hernandez@tienda.com',2),('LORM750404DD4','Maria','Lopez','Ramirez','5511223344','maria.lopez@tienda.com',1),('MART850625HH8','Teresa','Martinez','Garcia','5555667788','teresa.martinez@tienda.com',3),('ROGE800505EE5','Carlos','Gonzalez','Romero','5522334455','carlos.gonzalez@tienda.com',2),('SAVA880115FF6','Ana','Solis','Vargas','5533445566','ana.solis@tienda.com',1);
/*!40000 ALTER TABLE `encargado` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `num_seguimiento`
--

DROP TABLE IF EXISTS `num_seguimiento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `num_seguimiento` (
  `idCaso` int NOT NULL AUTO_INCREMENT,
  `idCliente` int NOT NULL,
  `TipoCaso` enum('FAC','ACL','DEV','DUD') NOT NULL,
  `FechaCreacion` datetime NOT NULL,
  PRIMARY KEY (`idCaso`),
  KEY `idCliente` (`idCliente`),
  CONSTRAINT `num_seguimiento_ibfk_1` FOREIGN KEY (`idCliente`) REFERENCES `cliente` (`idCliente`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `num_seguimiento`
--

LOCK TABLES `num_seguimiento` WRITE;
/*!40000 ALTER TABLE `num_seguimiento` DISABLE KEYS */;
INSERT INTO `num_seguimiento` VALUES (1,1,'DUD','2025-10-18 14:30:00'),(2,2,'DEV','2025-10-19 10:15:00'),(3,1,'ACL','2025-10-20 11:00:00');
/*!40000 ALTER TABLE `num_seguimiento` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `producto`
--

DROP TABLE IF EXISTS `producto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto` (
  `idProducto` int NOT NULL AUTO_INCREMENT,
  `NombreProducto` varchar(100) NOT NULL,
  `PrecioProducto` decimal(10,2) NOT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `Disponibilidad` tinyint(1) NOT NULL DEFAULT '1',
  `CodigoArea` int NOT NULL,
  `idDescuento` int DEFAULT NULL,
  PRIMARY KEY (`idProducto`),
  KEY `CodigoArea` (`CodigoArea`),
  KEY `idDescuento` (`idDescuento`),
  CONSTRAINT `producto_ibfk_1` FOREIGN KEY (`CodigoArea`) REFERENCES `area` (`CodigoArea`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `producto_ibfk_2` FOREIGN KEY (`idDescuento`) REFERENCES `descuento` (`idDescuento`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=504 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `producto`
--

LOCK TABLES `producto` WRITE;
/*!40000 ALTER TABLE `producto` DISABLE KEYS */;
INSERT INTO `producto` VALUES (101,'Televisión LED 50\"',8500.00,'Smart TV 4K UHD',1,10,2),(102,'Laptop Gamer',22000.00,'Laptop con tarjeta gráfica dedicada',1,10,NULL),(103,'Audífonos Bluetooth',1800.00,'Cancelación de ruido activa, 20hrs de batería',1,10,1),(104,'Mouse Inalámbrico',450.00,'Mouse ergonómico recargable',1,10,NULL),(105,'Teclado Mecánico RGB',2100.00,'Switch azul, layout en español',1,10,2),(201,'Camisa de Lino',750.00,'Camisa casual manga larga',1,20,1),(202,'Zapatos de Piel',1200.00,'Zapatos formales color negro',1,20,1),(203,'Jeans de Mezclilla',899.00,'Corte recto, color azul oscuro',1,20,NULL),(204,'Cinturón de Piel',500.00,'Hebilla de acero inoxidable',1,20,1),(301,'Cafetera de Goteo',950.00,'Capacidad 12 tazas, programable',1,30,2),(302,'Juego de Sábanas Queen',1100.00,'Algodón 400 hilos, color blanco',1,30,NULL),(303,'Podadora Eléctrica',3200.00,'1500W, bolsa recolectora',1,30,NULL),(401,'Bloques de Construcción (Set Grande)',1500.00,'+500 piezas, edad 5+',1,40,1),(402,'Muñeca Articulada',600.00,'Incluye 3 cambios de ropa',1,40,NULL),(403,'Auto a Control Remoto',750.00,'Batería recargable, escala 1:16',0,40,NULL),(501,'Balón de Fútbol No. 5',680.00,'Balón oficial de liga, piel sintética',1,50,NULL),(502,'Tapete de Yoga',490.00,'6mm de grosor, antiderrapante',1,50,1),(503,'Pesas (Set de 2)',1300.00,'Mancuernas ajustables de 20kg (10kg c/u)',1,50,2);
/*!40000 ALTER TABLE `producto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ticket`
--

DROP TABLE IF EXISTS `ticket`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket` (
  `NumTicket` int NOT NULL AUTO_INCREMENT,
  `FechaCompra` datetime NOT NULL,
  `idCliente` int NOT NULL,
  PRIMARY KEY (`NumTicket`),
  KEY `idCliente` (`idCliente`),
  CONSTRAINT `ticket_ibfk_1` FOREIGN KEY (`idCliente`) REFERENCES `cliente` (`idCliente`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1003 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ticket`
--

LOCK TABLES `ticket` WRITE;
/*!40000 ALTER TABLE `ticket` DISABLE KEYS */;
INSERT INTO `ticket` VALUES (1001,'2025-10-20 13:45:10',1),(1002,'2025-10-20 15:10:25',2);
/*!40000 ALTER TABLE `ticket` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ticket_detalle`
--

DROP TABLE IF EXISTS `ticket_detalle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_detalle` (
  `idTicketDetalle` int NOT NULL AUTO_INCREMENT,
  `NumTicket` int NOT NULL,
  `idProducto` int NOT NULL,
  `Cantidad` int NOT NULL,
  `PrecioVenta` decimal(10,2) NOT NULL,
  PRIMARY KEY (`idTicketDetalle`),
  KEY `NumTicket` (`NumTicket`),
  KEY `idProducto` (`idProducto`),
  CONSTRAINT `ticket_detalle_ibfk_1` FOREIGN KEY (`NumTicket`) REFERENCES `ticket` (`NumTicket`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `ticket_detalle_ibfk_2` FOREIGN KEY (`idProducto`) REFERENCES `producto` (`idProducto`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ticket_detalle`
--

LOCK TABLES `ticket_detalle` WRITE;
/*!40000 ALTER TABLE `ticket_detalle` DISABLE KEYS */;
INSERT INTO `ticket_detalle` VALUES (1,1001,101,1,8450.00),(2,1001,201,2,637.50),(3,1002,102,1,22000.00),(4,1002,201,1,637.50),(5,1002,202,1,1020.00);
/*!40000 ALTER TABLE `ticket_detalle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `turno`
--

DROP TABLE IF EXISTS `turno`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `turno` (
  `idTurno` int NOT NULL AUTO_INCREMENT,
  `NombreTurno` varchar(50) NOT NULL,
  PRIMARY KEY (`idTurno`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `turno`
--

LOCK TABLES `turno` WRITE;
/*!40000 ALTER TABLE `turno` DISABLE KEYS */;
INSERT INTO `turno` VALUES (1,'Matutino'),(2,'Vespertino'),(3,'Nocturno');
/*!40000 ALTER TABLE `turno` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-10 12:43:03
