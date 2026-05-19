# 🛒 CLOUZIE – E-commerce Web Application

## 📌 Overview
CLOUZIE is a full-featured e-commerce web application built using Django.  
It provides a complete shopping experience including product browsing, cart management, checkout, payments, order tracking, and admin control.

The system focuses on real-world business logic, especially pricing, offers, coupons, wallet refunds, and sales analytics.

---

## 🚀 Features

### 👤 User Features
- User registration & login (OTP-based)
- Product browsing with search, filter, and sorting
- Wishlist management
- Cart system
- Secure checkout
- Multiple payment methods:
  - Cash on Delivery (COD)
  - Razorpay (Online Payment)
  - Wallet payment
- Coupon application during checkout
- Order history & tracking
- Cancel and return requests
- Invoice generation (PDF)

---

### 🛍️ Product & Offer System
- Product variants (size, color, stock)
- Product-level offers
- Category-level offers
- Automatic best-offer selection
- Coupon system with:
  - Percentage and fixed discounts
  - Minimum purchase rules
  - Maximum discount limits

---

### 💰 Wallet System
- Wallet for each user
- Refund handling:
  - Instant refund for cancellations
  - Refund after admin approval for returns
- Wallet transaction tracking
- Wallet payment support

---

### 📊 Admin Features
- Product & category management
- Offer management (product & category)
- Coupon management
- Order management
- Return request handling
- Sales dashboard:
  - Revenue tracking
  - Order volume
  - Time-based analytics (daily, weekly, monthly, yearly)

---

## 🧠 Core Business Logic

- Pricing Flow
  - Original price → Offer discount → Coupon discount → Final amount

- Refund Logic
  - Refunds are calculated based on the actual paid amount
  - Handles partial cancellations and returns correctly

- Order Lifecycle
  - PENDING → CONFIRMED → SHIPPED → DELIVERED
  - Supports partial cancellations and returns

---

## 🛠️ Tech Stack

- Backend: Django  
- Frontend: HTML, CSS, Tailwind CSS, JavaScript  
- Database: PostgreSQL / SQLite  
- Payment Gateway: Razorpay  
- PDF Generation: ReportLab  

---

## 📁 Project Modules

- accounts/ → Authentication & user handling  
- cart/ → Cart logic  
- orders/ → Orders, payments, returns  
- adminpanel/ → Admin dashboard & management  
- wallet/ → Wallet and refunds  
- utils/ → Offer and pricing logic  

---

## ⚠️ Notes

- COD is restricted for high-value orders  
- Refunds are based on actual transaction values  
- System supports partial cancellations and returns  

---

## 📌 Improvements (In Progress)

- Ratings & reviews system  
- Performance optimization  
- Enhanced validation & UX improvements  

---

## 👨‍💻 Developer

Developed as a full-stack Django project focusing on real-world e-commerce workflows and business lo
