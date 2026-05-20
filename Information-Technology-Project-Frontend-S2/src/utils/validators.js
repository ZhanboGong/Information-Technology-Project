export const Validators = {
  username: (val) => /^[a-zA-Z0-9][a-zA-Z0-9_-]{2,18}[a-zA-Z0-9]$/.test(val),
  password: (val) => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[^\s]{8,32}$/.test(val),
  score: (val) => /^(\d{1,2}(\.\d{1,2})?|100(\.0{1,2})?)$/.test(val)
};