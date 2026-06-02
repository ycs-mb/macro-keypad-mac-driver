use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct AppError(pub String);

impl From<std::io::Error> for AppError {
    fn from(e: std::io::Error) -> Self { AppError(e.to_string()) }
}
impl From<serde_json::Error> for AppError {
    fn from(e: serde_json::Error) -> Self { AppError(e.to_string()) }
}
impl From<String> for AppError {
    fn from(s: String) -> Self { AppError(s) }
}
impl From<&str> for AppError {
    fn from(s: &str) -> Self { AppError(s.to_string()) }
}
impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

pub type AppResult<T> = Result<T, AppError>;
