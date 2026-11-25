# Build environment for the Android app (JDK + Android SDK + Gradle), so nothing
# needs installing on the PC. See android/build.ps1.
FROM eclipse-temurin:21-jdk

ARG CMDLINE_TOOLS=16111833
ARG GRADLE_VERSION=9.9.2
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=$PATH:/opt/android-sdk/cmdline-tools/latest/bin:/opt/gradle/bin

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends unzip curl >/dev/null \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p $ANDROID_HOME/cmdline-tools \
 && curl -sSL -o /tmp/tools.zip https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS}_latest.zip \
 && unzip -q /tmp/tools.zip -d $ANDROID_HOME/cmdline-tools \
 && mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest \
 && rm /tmp/tools.zip \
 && yes | sdkmanager --licenses >/dev/null \
 && sdkmanager "platforms;android-36" "build-tools;36.1.0" >/dev/null

RUN curl -sSL -o /tmp/gradle.zip https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip \
 && unzip -q /tmp/gradle.zip -d /opt \
 && mv /opt/gradle-${GRADLE_VERSION} /opt/gradle \
 && rm /tmp/gradle.zip

WORKDIR /project
