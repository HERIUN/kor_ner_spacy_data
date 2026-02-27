find /home/dgkang/eznero/data_prepare -name "*.zip" | while read zip; do
    dir=$(dirname "$zip")
    name=$(basename "$zip" .zip)
    echo "압축해제: $name"
    unzip -q -o -O CP949 "$zip" -d "$dir/$name"
done && echo "완료"