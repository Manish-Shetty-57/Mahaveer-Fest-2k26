/**
 * MAHAVEERA FEST 2K26 - MongoDB Production Schema & Validation Rules
 * Sri Mahaveera College, Moodbidri (Held on 30 October 2026)
 *
 * This script initializes collections with strict JSON Schema validators,
 * compound indexes, and aggregation pipelines.
 */

// Connect to the target database
const db = db.getSiblingDB("mahaveera_fest_2k26");

// ============================================================================
// 1. Colleges Collection
// ============================================================================
db.createCollection("colleges", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "_id",
        "college_name",
        "faculty_coordinator_name",
        "faculty_phone",
        "faculty_email",
        "total_students_registered",
        "created_at",
        "updated_at"
      ],
      properties: {
        _id: {
          bsonType: "string", // UUID string representation
          description: "Unique UUID identifier for the college"
        },
        college_name: {
          bsonType: "string",
          minLength: 3,
          maxLength: 255,
          description: "Unique name of the participating PU College"
        },
        faculty_coordinator_name: {
          bsonType: "string",
          minLength: 2,
          maxLength: 255,
          description: "Full name of faculty coordinator"
        },
        faculty_phone: {
          bsonType: "string",
          pattern: "^(\\+?[0-9]{10,15})$",
          description: "10-15 digit phone contact"
        },
        faculty_email: {
          bsonType: "string",
          pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
          description: "Valid email address of the coordinator"
        },
        total_students_registered: {
          bsonType: "int",
          minimum: 0,
          maximum: 25, // Rule 1: Maximum 25 unique students cap
          description: "Distinct student headcount registered across all events (0-25)"
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
});

// Indexes for Colleges
db.colleges.createIndex({ college_name: 1 }, { unique: true, collation: { locale: "en", strength: 2 } });
db.colleges.createIndex({ faculty_email: 1 });


// ============================================================================
// 2. Students Collection
// ============================================================================
db.createCollection("students", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "college_id", "student_name", "puc_year", "created_at", "updated_at"],
      properties: {
        _id: {
          bsonType: "string", // UUID string
          description: "Unique UUID identifier for student"
        },
        college_id: {
          bsonType: "string",
          description: "Reference to colleges._id"
        },
        student_name: {
          bsonType: "string",
          minLength: 2,
          maxLength: 255,
          description: "Student full name as per college ID card"
        },
        puc_year: {
          enum: ["1st PUC", "2nd PUC"],
          description: "PUC class year"
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
});

// Indexes for Students
db.students.createIndex({ college_id: 1 });
db.students.createIndex(
  { college_id: 1, student_name: 1, puc_year: 1 },
  { unique: true, collation: { locale: "en", strength: 2 } }
);


// ============================================================================
// 3. Registrations Collection
// ============================================================================
db.createCollection("registrations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "_id",
        "college_id",
        "event_name",
        "department",
        "team_members",
        "created_at",
        "updated_at"
      ],
      properties: {
        _id: {
          bsonType: "string", // UUID string
          description: "Unique UUID identifier for registration"
        },
        college_id: {
          bsonType: "string",
          description: "Reference to colleges._id"
        },
        event_name: {
          bsonType: "string",
          description: "Official event name"
        },
        department: {
          enum: ["SCIENCE", "COMMERCE", "IT", "HUMANITIES"],
          description: "Department organizing the event"
        },
        team_members: {
          bsonType: "array",
          minItems: 1,
          maxItems: 4, // Max team size in fest (Math Crunch = 4)
          uniqueItems: true,
          items: {
            bsonType: "string",
            description: "Array of student UUID references"
          },
          description: "List of participating student UUIDs"
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
});

// Indexes for Registrations
// Rule: Only one team per college per event
db.registrations.createIndex({ college_id: 1, event_name: 1 }, { unique: true });
db.registrations.createIndex({ department: 1 });
db.registrations.createIndex({ "team_members": 1 });


// ============================================================================
// Aggregation Pipeline: Calculate Unique Students per College
// ============================================================================
/**
 * Pipeline to calculate the distinct participating student count for a college:
 *
 * db.registrations.aggregate([
 *   { $match: { college_id: "<COLLEGE_UUID>" } },
 *   { $unwind: "$team_members" },
 *   { $group: { _id: "$college_id", unique_students: { $addToSet: "$team_members" } } },
 *   { $project: { unique_student_count: { $size: "$unique_students" } } }
 * ]);
 */
