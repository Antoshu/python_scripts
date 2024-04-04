
//cargo build --target=x86_64-pc-windows-gnu
use std::{env, fs, io::Write};

fn main() {
    let current_exe = env::current_exe().unwrap();
    let mut filepath = current_exe.to_owned();
    filepath.set_file_name("download_image.py");
    
    let req = reqwest::blocking::get("https://raw.githubusercontent.com/Antoshu/python_scripts/main/download_image.py");
    let resp = req.unwrap();
    let bytes = resp.bytes().unwrap();
    let mut file = fs::File::create(&filepath).expect("Could not create script file, check permisisons");

    file.write_all(&bytes).unwrap();



}