FROM node:20-alpine
WORKDIR /app
# package-lock.json은 일부러 안 가져온다 — 로컬(Windows/glibc 등)에서 만든
# lockfile을 그대로 이 musl(alpine) 컨테이너에서 쓰면, rollup의 플랫폼별
# 네이티브 바이너리(optionalDependency)가 npm의 알려진 버그(npm/cli#4828)로
# 잘못 설치돼 "Cannot find module @rollup/rollup-linux-x64-musl" 에러가 난다.
# package.json만 넣고 컨테이너 안에서(=실제 musl 플랫폼에서) 매번 새로
# resolve하게 하면 이 문제를 원천적으로 피할 수 있다.
COPY package.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]